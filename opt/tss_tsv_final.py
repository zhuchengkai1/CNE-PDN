import hspice_gpt
import numpy as np
import os
import shutil
import pandas as pd
import torch
import torch.nn as nn
import joblib
import pickle
import warnings
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from scipy.fft import rfft, irfft, rfftfreq
from scipy.interpolate import interp1d

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

from src.main import main_solver


# ==========================================
# 0. network
# ==========================================
class TinyRobustMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(8, 64),
            nn.BatchNorm1d(64),
            nn.SiLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 64),
            nn.BatchNorm1d(64),
            nn.SiLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.SiLU(),
            nn.Linear(32, 10)
        )

    def forward(self, x):
        return self.net(x)


print("🚀  Surrogate Model and Scalers...")
model = TinyRobustMLP()
model.load_state_dict(torch.load("tiny_robust_mlp.pth", map_location='cpu'))
model.eval()
scaler_x = joblib.load("scaler_x.pkl")
scaler_y = joblib.load("scaler_y.pkl")


TMP_SPICE_DIR = "tmp_spice"
net = 23
F_IDEAL_GHZ = 2.0
V_DD = 0.50

V_TH = 0.30
ALPHA = 2.0


C_cont = 2.253e-14
C_insulator = 2.915e-13
C_bump = 2.036e-13
C_tsv = 9.602e-13
L_total = 8.994e-12
R_tsv = 1.097e+03
C_total = 3.119e-13
R_dc = 4.546e-02
R_ac = 5e-6



def decode_pdn_params(z_pdn):
    def sigmoid(x): return 1 / (1 + np.exp(-x))

    pdn_wide = 10.0 + 8.0 * sigmoid(z_pdn[0])
    h_pdn_1 = 0.9 + 0.4 * sigmoid(z_pdn[1])
    return pdn_wide, h_pdn_1


def penalty(): return 10.0 + np.random.rand()


def generate_initial_place(n=23, n_tsv=100):
    place = np.zeros((n, n), dtype=int)
    count = 0
    for row in range(n - 1, -1, -1):
        for col in range(n):
            if count < n_tsv:
                place[row, col] = 1
                count += 1
            else:
                break
        if count >= n_tsv: break
    return place


def place_to_x0(place, low=-0.4, high=0.4):
    flat = place.flatten()
    x0 = np.zeros_like(flat, dtype=float)
    for i, v in enumerate(flat):
        x0[i] = (low if v == 1 else high) + 0.05 * np.random.randn()
    return x0


def save_place_csv(place, out_path):
    df = pd.DataFrame(place.astype(int), columns=[f"col_{i}" for i in range(place.shape[1])])
    df.insert(0, "row", np.arange(place.shape[0]))
    df.to_csv(out_path, index=False)


def apply_koz_mask(z_tsv, n=23):
    z_masked = np.asarray(z_tsv).copy()

    def mask_region(x_s, x_e, y_s, y_e):
        for i in range(x_s, x_e + 1):
            for j in range(y_s, y_e + 1):
                if 0 <= i < n and 0 <= j < n: z_masked[i * n + j] = 1e9

    mask_region(6, 8, 6, 8)
    mask_region(13, 17, 18, 20)
    mask_region(18, 20, 7, 8)
    return z_masked


def decode_tsv_stage1(z, n=23):
    z = apply_koz_mask(z, n)
    z_grid = z.reshape(n, n)[n - 22:, n - 22:]
    blocks = []
    for i in range(0, 22, 2):
        for j in range(0, 22, 2): blocks.append(z_grid[i:i + 2, j:j + 2].mean())
    block_idx = np.argsort(np.array(blocks))[:25]
    tsv_idx = []
    for b in block_idx:
        bi, bj = (b // 11) * 2, (b % 11) * 2
        for dx in [0, 1]:
            for dy in [0, 1]: tsv_idx.append((n - 22 + bi + dx) * n + (n - 22 + bj + dy))
    return np.array(tsv_idx)


def decode_tsv_stage2(z, n_tsv=100):
    z = apply_koz_mask(z)
    return np.argsort(z)[:n_tsv]


def indices_to_place(indices, ncol=23):
    place = np.zeros((ncol, ncol), dtype=int)
    for idx in indices: place[idx // ncol, idx % ncol] = 1
    return place


# ==========================================
# 3.  IFFT
# ==========================================
def run_hybrid_eval_and_get_freq(z_tsv, z_pdn, iter_id, stage):
    pdn_wide, h_pdn_1 = decode_pdn_params(z_pdn)
    space = 28.0 - pdn_wide
    X_input = np.array([[pdn_wide, space, 50.0, 0.75, h_pdn_1, 1.0, float(net), h_pdn_1]], dtype=np.float32)

    try:
        X_scaled = scaler_x.transform(X_input)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        with torch.no_grad():
            Y_pred_scaled = model(X_tensor)
        Y_pred_real = np.power(10.0, scaler_y.inverse_transform(Y_pred_scaled.numpy()))[0]
        L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX = Y_pred_real
        C_pgax = C_pgcx = C_pgbx
    except:
        return None

    tsv_idx = decode_tsv_stage1(z_tsv) if stage == 1 else decode_tsv_stage2(z_tsv)
    place = indices_to_place(tsv_idx)

    out_dir = os.path.join(TMP_SPICE_DIR, f"run_{iter_id}")
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    try:
        _, flag = hspice_gpt.hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX,
                                        C_cont, C_insulator, C_bump, C_tsv, L_total, R_tsv, C_total,
                                        R_dc, R_ac, net, C_pgcx, C_pgax, out_dir, place)
        if flag != 0: return None

        df = pd.read_csv(os.path.join(out_dir, "result.csv")).dropna()
        if df.empty: return None

        F_ideal_Hz = F_IDEAL_GHZ * 1e9
        I_leak = 0.002
        t_total, dt = 10e-9, 1e-12
        N = int(t_total / dt)
        t_array = np.linspace(0, t_total, N, endpoint=False)
        window_mask = (t_array >= 1e-9) & (t_array <= 1.2e-9)

        def get_effective_voltage(spice_freqs, z_real, z_imag, peak_current):
            z_complex = z_real.values + 1j * z_imag.values
            i_t = np.ones(N) * I_leak
            i_t[window_mask] = peak_current
            I_f = rfft(i_t)
            freqs_fft = rfftfreq(N, dt)
            interp_func = interp1d(spice_freqs.values, z_complex, kind='linear', bounds_error=False,
                                   fill_value=(z_complex[0].real + 0j, z_complex[-1]))
            delta_v_t = irfft(I_f * interp_func(freqs_fft), n=N)
            return np.mean((V_DD - delta_v_t)[window_mask])

        V_eff = min(
            get_effective_voltage(df['freq'], df['Z_re_2_2'], df['Z_im_2_2'], 0.015e-9 * V_DD * F_ideal_Hz + 0.005),
            get_effective_voltage(df['freq'], df['Z_re_7_15'], df['Z_im_7_15'],
                                  0.008e-9 * V_DD * F_ideal_Hz + 0.002),
            get_effective_voltage(df['freq'], df['Z_re_15_4'], df['Z_im_15_4'],
                                  0.010e-9 * V_DD * F_ideal_Hz + 0.003))

        if V_eff <= V_TH:
            return None

        F_act = F_IDEAL_GHZ * ((V_eff - V_TH) / (V_DD - V_TH)) ** ALPHA

        penalty_w = 0.01 * max(0, pdn_wide - 14.0)
        penalty_h = 0.05 * max(0, h_pdn_1 - 1.1)
        final_freq = F_act - (penalty_w + penalty_h)

        if not np.isfinite(final_freq):
            return None

        return max(0.001, final_freq)
    except:
        return None


def objective_two_stage(z, iter_id, stage):
    z_tsv, z_pdn = z[:-2], z[-2:]
    freq = run_hybrid_eval_and_get_freq(z_tsv, z_pdn, iter_id, stage)
    return (F_IDEAL_GHZ - freq + 1e-6 * np.random.randn()) if freq is not None else penalty()


def create_tssbo_objective(stage, max_workers=8):
    def funct(X):
        X_np = X.cpu().detach().numpy() if torch.is_tensor(X) else np.array(X)
        if X_np.ndim == 1: X_np = X_np.reshape(1, -1)
        batch_size = X_np.shape[0]
        penalties = [0.0] * batch_size
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(objective_two_stage, X_np[i], f"stg{stage}_b{batch_size}_{i}", stage): i for i in
                       range(batch_size)}
            for future in as_completed(futures):
                try:
                    penalties[futures[future]] = future.result()
                except:
                    penalties[futures[future]] = penalty()

        return np.array(penalties, dtype=np.float32).reshape(-1)

    return funct


# ==========================================
# 4. main
# ==========================================
if __name__ == "__main__":
    NUM_RUNS = 3
    BATCH_SIZE = 24
    NMAX = 2400
    best_dir = "best_result"
    os.makedirs(best_dir, exist_ok=True)

    for run_idx in range(1, NUM_RUNS + 1):
        print(f"\n{'🔥' * 10}  {run_idx} / {NUM_RUNS}  {'🔥' * 10}")
        start_wall_time = time.time()

        if os.path.exists(TMP_SPICE_DIR): shutil.rmtree(TMP_SPICE_DIR)
        os.makedirs(TMP_SPICE_DIR)

        dim = 23 * 23 + 2
        bounds_array = np.array([[-0.5, 0.5]] * dim, dtype=np.float32)

        p_init1 = generate_initial_place(n=23, n_tsv=100)
        x0_stage1_np = np.vstack([np.concatenate([place_to_x0(p_init1), np.zeros(2)]) for _ in range(8)]).astype(
            np.float32)

        # Stage 1:
        pkl_s1 = f"run{run_idx}_stage1.pkl"
        main_solver(funct=create_tssbo_objective(stage=1, max_workers=8), dim=dim, bounds=bounds_array,
                    init_x=x0_stage1_np,
                    sigma=0.8, mu=0.5, batch_size=BATCH_SIZE, n_candidates=200, nMax=NMAX, k=dim * 3,
                    dataset_file=pkl_s1)


        with open(pkl_s1, "rb") as f:
            history1 = pickle.load(f)

        best_indices = np.argsort(history1[1].cpu().numpy().flatten())[:8]
        best_x_s1_raw = history1[0].cpu().numpy()[best_indices]

        x0_s2_list = []
        for i, x in enumerate(best_x_s1_raw):
            base_x = np.concatenate([place_to_x0(indices_to_place(decode_tsv_stage1(x[:-2]))), x[-2:]])
            if i == 0:

                x0_s2_list.append(base_x)
            else:

                noise = np.random.normal(loc=0.0, scale=0.25, size=base_x.shape)
                perturbed_x = base_x + noise
                perturbed_x = np.clip(perturbed_x, -0.5, 0.5)
                x0_s2_list.append(perturbed_x)

        x0_s2 = np.vstack(x0_s2_list).astype(np.float32)

        pkl_s2 = f"run{run_idx}_stage2.pkl"
        main_solver(funct=create_tssbo_objective(stage=2, max_workers=8), dim=dim, bounds=bounds_array, init_x=x0_s2,
                    sigma=0.4, batch_size=BATCH_SIZE, nMax=NMAX, k=dim * 3, dataset_file=pkl_s2)

        end_wall_time = time.time()
        total_min = (end_wall_time - start_wall_time) / 60.0

        with open(pkl_s2, "rb") as f:
            history2 = pickle.load(f)
        hist_y1 = history1[1].cpu().numpy().flatten()
        hist_y2 = history2[1].cpu().numpy().flatten()

        history_data = []
        g_best = float('inf')
        for stage, h_y in [("Stage 1", hist_y1), ("Stage 2", hist_y2)]:
            for val in h_y:
                g_best = min(g_best, val)
                history_data.append([stage, max(0.0, F_IDEAL_GHZ - val), max(0.0, F_IDEAL_GHZ - g_best)])

        csv_name = f"{total_min:.2f}min_Run{run_idx}_tssbo_history.csv"
        pd.DataFrame(history_data, columns=["Stage", "Current_Freq", "Best_Freq"]).to_csv(
        os.path.join(best_dir, csv_name), index=False)

        print(f"✅  {run_idx} end，time: {total_min:.2f} min，best freq: {F_IDEAL_GHZ - g_best:.4f} GHz")
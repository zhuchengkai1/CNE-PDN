import hspice_gpt
import numpy as np
import os
import shutil
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import torch
import pickle
import warnings
import time


from scipy.fft import rfft, irfft, rfftfreq
from scipy.interpolate import interp1d

warnings.filterwarnings("ignore")

from src.main import main_solver

TMP_SPICE_DIR = "tmp_spice"
L_AX = 1.0128e-9
L_BX = 9.0326e-10
L_CX = 1.07678e-10
R_AX = 0.001175
R_BX = 0.00023742
R_CX = 416.12076
C_psi = 4.8194e-14
C_sub = 8.4212e-14
C_pgax = C_pgbx = C_pgcx = 3.3633e-15
R_sub = 243.361
C_cont = 2.253e-14
C_insulator = 2.915e-13
C_bump = 2.036e-13
C_tsv = 9.602e-13
L_total = 8.994e-12
R_tsv = 1.097e+03
C_total = 3.119e-13
R_dc = 4.546e-02
R_ac = 5e-6
net = 23

F_IDEAL_GHZ = 2.5
V_DD = 0.70
V_TH = 0.30
ALPHA = 2.0

WALL_SPICE_TIME = 0.0



def penalty():

    return 10.0 + np.random.rand()


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
        if count >= n_tsv:
            break
    return place


def place_to_x0(place, low=-0.4, high=0.4):
    flat = place.flatten()
    x0 = np.zeros_like(flat, dtype=float)
    for i, v in enumerate(flat):
        if v == 1:
            x0[i] = low + 0.05 * np.random.randn()
        else:
            x0[i] = high + 0.05 * np.random.randn()
    return x0


def save_place_csv(place, out_path):
    df = pd.DataFrame(
        place.astype(int),
        columns=[f"col_{i}" for i in range(place.shape[1])]
    )
    df.insert(0, "row", np.arange(place.shape[0]))
    df.to_csv(out_path, index=False)


# ==========================================
# AIFM
# ==========================================
def apply_koz_mask(z_tsv, n=23):
    z_masked = np.asarray(z_tsv).copy()

    def mask_region(x_start, x_end, y_start, y_end):
        for i in range(x_start, x_end + 1):
            for j in range(y_start, y_end + 1):
                if 0 <= i < n and 0 <= j < n:
                    z_masked[i * n + j] = 1e9

    mask_region(4, 10, 4, 10)
    mask_region(9, 20, 17, 20)
    mask_region(16, 20, 5, 10)
    return z_masked


def decode_tsv_stage1(z, n=23):
    z = apply_koz_mask(z, n)
    z_grid = z.reshape(n, n)[n - 22:, n - 22:]
    blocks = []
    for i in range(0, 22, 2):
        for j in range(0, 22, 2):
            blocks.append(z_grid[i:i + 2, j:j + 2].mean())
    block_idx = np.argsort(np.array(blocks))[:25]
    tsv_idx = []
    for b in block_idx:
        bi, bj = (b // 11) * 2, (b % 11) * 2
        for dx in [0, 1]:
            for dy in [0, 1]:
                tsv_idx.append((n - 22 + bi + dx) * n + (n - 22 + bj + dy))
    return np.array(tsv_idx)


def decode_tsv_stage2(z, n_tsv=100):
    return np.argsort(apply_koz_mask(z))[:n_tsv]


def indices_to_place(indices, ncol=23):
    place = np.zeros((ncol, ncol), dtype=int)
    for idx in indices:
        place[idx // ncol, idx % ncol] = 1
    return place



def run_spice_and_get_freq(place, iter_id):
    out_dir = os.path.join(TMP_SPICE_DIR, f"run_{iter_id}")
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    try:
        _, flag = hspice_gpt.hspice_run(
            L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX,
            C_cont, C_insulator, C_bump, C_tsv, L_total, R_tsv, C_total,
            R_dc, R_ac, net, C_pgcx, C_pgax, out_dir, place
        )

        if flag != 0:
            return None

        result_csv = os.path.join(out_dir, "result.csv")
        if not os.path.exists(result_csv):
            return None

        df = pd.read_csv(result_csv).dropna()
        if df.empty:
            return None

        F_ideal_Hz = F_IDEAL_GHZ * 1e9
        I_peak_2_2 = 0.015e-9 * V_DD * F_ideal_Hz + 0.005
        I_peak_7_15 = 0.008e-9 * V_DD * F_ideal_Hz + 0.002
        I_peak_15_4 = 0.010e-9 * V_DD * F_ideal_Hz + 0.003
        I_leak = 0.002

        t_total, dt = 10e-9, 1e-12
        N = int(t_total / dt)
        t_array = np.linspace(0, t_total, N, endpoint=False)
        window_mask = (t_array >= 1e-9) & (t_array <= 1.2e-9)

        def get_effective_voltage(spice_freqs, z_real, z_imag, peak_current):
            spice_freqs = spice_freqs.values
            z_complex = z_real.values + 1j * z_imag.values
            i_t = np.ones(N) * I_leak
            i_t[window_mask] = peak_current
            I_f = rfft(i_t)
            freqs_fft = rfftfreq(N, dt)
            Z_f_aligned = interp1d(spice_freqs, z_complex, kind='linear',
                                   bounds_error=False, fill_value=(z_complex[0].real + 0j, z_complex[-1]))(
                freqs_fft)
            delta_v_t = irfft(I_f * Z_f_aligned, n=N)
            return np.mean((V_DD - delta_v_t)[window_mask])

        spice_f = df['freq']
        V_eff_2_2 = get_effective_voltage(spice_f, df['Z_re_2_2'], df['Z_im_2_2'], I_peak_2_2)
        V_eff_7_15 = get_effective_voltage(spice_f, df['Z_re_7_15'], df['Z_im_7_15'], I_peak_7_15)
        V_eff_15_4 = get_effective_voltage(spice_f, df['Z_re_15_4'], df['Z_im_15_4'], I_peak_15_4)

        V_actual = min(V_eff_2_2, V_eff_7_15, V_eff_15_4)

        if V_actual <= V_TH:
            return None

        F_actual_GHz = F_IDEAL_GHZ * ((V_actual - V_TH) / (V_DD - V_TH)) ** ALPHA
        if not np.isfinite(F_actual_GHz):
            return None

        return F_actual_GHz

    except Exception:
        return None


def objective_two_stage(z, iter_id, stage):
    if stage == 1:
        tsv_idx = decode_tsv_stage1(z)
    else:
        tsv_idx = decode_tsv_stage2(z)

    place = indices_to_place(tsv_idx)
    freq = run_spice_and_get_freq(place, iter_id)

    if freq is None: return penalty()
    return F_IDEAL_GHZ - freq + 1e-6 * np.random.randn()



def create_tssbo_objective(stage, max_workers=8):
    def funct(X):
        global WALL_SPICE_TIME

        if torch.is_tensor(X):
            X_np = X.cpu().detach().numpy()
        else:
            X_np = np.array(X)
        if X_np.ndim == 1: X_np = X_np.reshape(1, -1)

        batch_size = X_np.shape[0]
        penalties = [0.0] * batch_size

        t_spice_start = time.time()

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(objective_two_stage, X_np[i], f"stg{stage}_b{batch_size}_{i}", stage): i for i in
                       range(batch_size)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    penalties[idx] = future.result()
                except Exception:
                    penalties[idx] = penalty()

        t_spice_end = time.time()
        WALL_SPICE_TIME += (t_spice_end - t_spice_start)

        return np.array(penalties, dtype=np.float32).reshape(-1, 1)

    return funct



if __name__ == "__main__":
    NUM_RUNS = 3
    best_dir = "best_result"
    os.makedirs(best_dir, exist_ok=True)

    dim = 23 * 23
    bounds_array = np.array([[-0.5, 0.5]] * dim, dtype=np.float32)
    initial_places = []

    p_init1 = generate_initial_place(n=23, n_tsv=100)
    save_place_csv(p_init1, os.path.join(best_dir, "initial_place_bottom.csv"))
    initial_places.append(place_to_x0(p_init1))
    initial_places.append(place_to_x0(p_init1))
    x0_stage1_np = np.vstack(initial_places).astype(np.float32)

    for run_idx in range(1, NUM_RUNS + 1):
        print("\n" + "🔥" * 25)
        print("🔥" * 25)

        WALL_SPICE_TIME = 0.0
        total_start_time = time.time()

        if os.path.exists(TMP_SPICE_DIR): shutil.rmtree(TMP_SPICE_DIR)
        os.makedirs(TMP_SPICE_DIR)

        pkl_stage1 = f"tssbo_stage1_history_Run{run_idx}.pkl"
        pkl_stage2 = f"tssbo_stage2_history_Run{run_idx}.pkl"

        # ---------------------------------------------------------
        # 1.Stage 1
        # ---------------------------------------------------------
        print("\n" + "-" * 40)
        print(f"[Run {run_idx}]  Stage 1 ")
        main_solver(
            funct=create_tssbo_objective(stage=1, max_workers=8), dim=dim, bounds=bounds_array, init_x=x0_stage1_np,
            sigma=0.4, mu=0.5, batch_size=24, n_candidates=200, nMax=2400, k=dim * 3,
            dataset_file=pkl_stage1
        )


        print(f"\n[Run {run_idx}] ")
        with open(pkl_stage1, "rb") as f:
            history1 = pickle.load(f)

        best_x_stage1_raw = history1[0].cpu().numpy()[np.argsort(history1[1].cpu().numpy().flatten())[:2]]
        x0_stage2_np = np.vstack(
            [place_to_x0(indices_to_place(decode_tsv_stage1(x))) for x in best_x_stage1_raw]).astype(np.float32)

        # ---------------------------------------------------------
        # 3. Stage 2
        # ---------------------------------------------------------
        print("\n" + "-" * 40)
        print(f"[Run {run_idx}] 🚀 Stage 2 start")
        main_solver(
            funct=create_tssbo_objective(stage=2, max_workers=8), dim=dim, bounds=bounds_array, init_x=x0_stage2_np,
            sigma=0.1, batch_size=24, nMax=2400, k=dim * 3,
            dataset_file=pkl_stage2
        )


        print(f"\n[Run {run_idx}] ...")
        with open(pkl_stage2, "rb") as f:
            history2_final = pickle.load(f)

        hist_y1 = history1[1].cpu().numpy().flatten()
        hist_x1 = history1[0].cpu().numpy()
        hist_y2 = history2_final[1].cpu().numpy().flatten()
        hist_x2 = history2_final[0].cpu().numpy()

        best_idx1, best_idx2 = np.argmin(hist_y1), np.argmin(hist_y2)
        if hist_y2[best_idx2] < hist_y1[best_idx1]:
            best_penalty_final, best_tsv_idx = hist_y2[best_idx2], decode_tsv_stage2(hist_x2[best_idx2])
        else:
            best_penalty_final, best_tsv_idx = hist_y1[best_idx1], decode_tsv_stage1(hist_x1[best_idx1])

        final_system_frequency = F_IDEAL_GHZ - best_penalty_final
        save_place_csv(indices_to_place(best_tsv_idx), os.path.join(best_dir, f"Run{run_idx}_best_place_tssbo.csv"))


        print(f"[{run_idx}/{NUM_RUNS}] ")
        t_base_start = time.time()
        init_freq = run_spice_and_get_freq(p_init1, f"baseline_run{run_idx}")
        WALL_SPICE_TIME += (time.time() - t_base_start)
        if init_freq is None: init_freq = 0.0


        total_end_time = time.time()
        total_minutes = (total_end_time - total_start_time) / 60.0
        spice_minutes = WALL_SPICE_TIME / 60.0
        algo_minutes = total_minutes - spice_minutes


        history_data = []
        global_best_penalty = float('inf')

        for val in hist_y1:
            if val < global_best_penalty: global_best_penalty = val
            history_data.append(
                ["Stage 1", 0.0 if val >= 10.0 else F_IDEAL_GHZ - val, max(0.0, F_IDEAL_GHZ - global_best_penalty)])

        for val in hist_y2:
            if val < global_best_penalty: global_best_penalty = val
            history_data.append(
                ["Stage 2", 0.0 if val >= 10.0 else F_IDEAL_GHZ - val, max(0.0, F_IDEAL_GHZ - global_best_penalty)])


        history_csv_name = f"{total_minutes:.2f}min_Run{run_idx}_tssbo_optimization_history.csv"
        pd.DataFrame(history_data,
                     columns=["Optimization_Stage", "Current_Eval_Freq_GHz", "Historical_Best_Freq_GHz"]).to_csv(
            os.path.join(best_dir, history_csv_name), index=False)


        print("\n" + "🏆" * 20)
        print(f"✅  {run_idx} 2 stages end！")
        print(f"📉 baseline freq: {init_freq:.4f} GHz")
        print(f"📈 best freq: {final_system_frequency:.4f} GHz")
        print(f"🚀 freq better: {(final_system_frequency - init_freq):.4f} GHz")
        print("-" * 40)
        print(f"⏱️ SPICE time: {spice_minutes:.2f} min")
        print(f"⏱️ OPT time: {algo_minutes:.2f} min")
        print(f"⏱️ whole time: {total_minutes:.2f} min")
        print(f"📂 history file was in: {history_csv_name}")
        print("🏆" * 20 + "\n")

    print("🎉 end")
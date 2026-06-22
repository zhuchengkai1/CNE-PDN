import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("DECOMP_AC_POINTS", "25")

import numpy as np
import shutil
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import torch
import pickle
import warnings
import time

# Import custom modules
import hspice_gpt
from routing_constraints import build_routing_keepout, save_keepout_artifacts
from benchmark_config import get_benchmark

from scipy.fft import rfft, irfft, rfftfreq
from scipy.interpolate import interp1d
from src.main import main_solver

warnings.filterwarnings("ignore")

# ==========================================
# Physical Constants & Global Configuration
# ==========================================
BENCHMARK = get_benchmark()
GRID_N = BENCHMARK.net
N_TSV = BENCHMARK.n_tsv
STAGE1_BLOCK = BENCHMARK.stage1_block

print(f"[*] Loaded Benchmark: {BENCHMARK.name}")
print(f"[*] Grid Size: {GRID_N}x{GRID_N}, Total TSVs: {N_TSV}, Macro Block Size: {STAGE1_BLOCK}x{STAGE1_BLOCK}")

# Configurable paths for open-source usage
TMP_SPICE_DIR = os.environ.get("TMP_SPICE_DIR", "./tmp_spice")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", f"./results_{BENCHMARK.name}")

L_AX, L_BX, L_CX = 1.0128e-9, 9.0326e-10, 1.07678e-10
R_AX, R_BX, R_CX = 0.001175, 0.00023742, 416.12076
C_psi, C_sub, R_sub = 4.8194e-14, 8.4212e-14, 243.361
C_pgax = C_pgbx = C_pgcx = 3.3633e-15
C_cont, C_insulator, C_bump = 2.253e-14, 2.915e-13, 2.036e-13
C_tsv, L_total, R_tsv = 9.602e-13, 8.994e-12, 1.097e+03
C_total, R_dc, R_ac = 3.119e-13, 4.546e-02, 5e-6

F_IDEAL_GHZ = 2.0
V_DD = 0.70
V_TH = 0.30
ALPHA = 2.0

WALL_SPICE_TIME = 0.0
SIM_MAX_WORKERS = int(os.environ.get("SIM_MAX_WORKERS", "8"))
OPT_BATCH_SIZE = int(os.environ.get("OPT_BATCH_SIZE", "15"))

# Resource allocation: Coarse search vs Fine-tuning
STAGE1_NMAX = int(os.environ.get("STAGE1_NMAX", "1600"))
STAGE2_NMAX = int(os.environ.get("STAGE2_NMAX", "3200"))

# Generate routing constraints
ROUTING_KEEP_OUT_MASK, ROUTING_PATHS = build_routing_keepout(
    n=GRID_N,
    route_spacing=BENCHMARK.route_spacing,
    include_chiplet_body=False,
)

# ==========================================
# Utility & Helper Functions
# ==========================================
def penalty():
    return 10.0 + np.random.rand()

def generate_initial_place(n=GRID_N, n_tsv=N_TSV):
    """Fill TSVs from bottom to top until n_tsv is reached."""
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

def place_to_x0(place, low=-0.05, high=0.05):
    """Break gravitational trap, narrow mapping bounds to [-0.05, 0.05]"""
    flat = place.flatten()
    x0 = np.zeros_like(flat, dtype=float)
    for i, v in enumerate(flat):
        if v == 1:
            x0[i] = low + 0.01 * np.random.randn()
        else:
            x0[i] = high + 0.01 * np.random.randn()
    return x0

def save_place_csv(place, out_path):
    df = pd.DataFrame(
        place.astype(int),
        columns=[f"col_{i}" for i in range(place.shape[1])]
    )
    df.insert(0, "row", np.arange(place.shape[0]))
    df.to_csv(out_path, index=False)

# ==========================================
# Decoding & Mapping Functions
# ==========================================
def apply_koz_mask(z_tsv, n=GRID_N):
    z_masked = np.asarray(z_tsv).copy()
    keepout = ROUTING_KEEP_OUT_MASK
    z_masked[keepout.reshape(-1)] = 1e9  # Penalize points in the keep-out zone
    return z_masked

def decode_tsv_stage1(z, n=GRID_N, n_tsv=N_TSV, block_size=STAGE1_BLOCK):
    z = apply_koz_mask(z, n)
    z_grid = z.reshape(n, n)

    usable_n = (n // block_size) * block_size
    offset = n - usable_n
    z_grid = z_grid[offset:, offset:]

    blocks = []
    block_coords = []

    for i in range(0, usable_n, block_size):
        for j in range(0, usable_n, block_size):
            blocks.append(z_grid[i:i + block_size, j:j + block_size].mean())
            block_coords.append((i + offset, j + offset))

    num_blocks = n_tsv // (block_size * block_size)
    block_idx = np.argsort(np.array(blocks))[:num_blocks]

    tsv_idx = []
    for b in block_idx:
        bi, bj = block_coords[b]
        for dx in range(block_size):
            for dy in range(block_size):
                tsv_idx.append((bi + dx) * n + (bj + dy))

    return np.array(tsv_idx)

def decode_tsv_stage2(z, n_tsv=N_TSV):
    return np.argsort(apply_koz_mask(z))[:n_tsv]

def indices_to_place(indices, ncol=GRID_N):
    place = np.zeros((ncol, ncol), dtype=int)
    for idx in indices:
        place[idx // ncol, idx % ncol] = 1
    return place

# ==========================================
# SPICE Simulation Module
# ==========================================
def run_spice_and_get_freq(place, iter_id):
    out_dir = os.path.join(TMP_SPICE_DIR, f"run_{iter_id}")
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    try:
        _, flag = hspice_gpt.hspice_run(
            L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX,
            C_cont, C_insulator, C_bump, C_tsv, L_total, R_tsv, C_total,
            R_dc, R_ac, GRID_N, C_pgcx, C_pgax, out_dir, place
        )

        if flag != 0: return None
        result_csv = os.path.join(out_dir, "result.csv")
        if not os.path.exists(result_csv): return None

        df = pd.read_csv(result_csv).dropna()
        if df.empty: return None

        F_ideal_Hz = F_IDEAL_GHZ * 1e9
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
                                   bounds_error=False, fill_value=(z_complex[0].real + 0j, z_complex[-1]))(freqs_fft)
            delta_v_t = irfft(I_f * Z_f_aligned, n=N)
            return np.mean((V_DD - delta_v_t)[window_mask])

        spice_f = df['freq']
        v_effs = []

        for mon in BENCHMARK.monitors:
            peak_current = mon.peak_coeff * F_ideal_Hz + mon.peak_offset
            col_re = f"Z_re_{mon.row}_{mon.col}"
            col_im = f"Z_im_{mon.row}_{mon.col}"

            if col_re not in df.columns or col_im not in df.columns:
                return None

            v_eff = get_effective_voltage(spice_f, df[col_re], df[col_im], peak_current)
            v_effs.append(v_eff)

        V_actual = min(v_effs)

        if V_actual <= V_TH:
            return None

        F_actual_GHz = F_IDEAL_GHZ * ((V_actual - V_TH) / (V_DD - V_TH)) ** ALPHA
        if not np.isfinite(F_actual_GHz): return None

        return F_actual_GHz

    except Exception as e:
        print(f"Simulation Error: {e}")
        return None

def objective_two_stage(z, iter_id, stage):
    if stage == 1:
        tsv_idx = decode_tsv_stage1(z)
    else:
        tsv_idx = decode_tsv_stage2(z)

    place = indices_to_place(tsv_idx)
    freq = run_spice_and_get_freq(place, iter_id)

    if freq is None: return penalty()

    # Pure electrical performance objective without artificial penalties
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
            done_count = 0
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    penalties[idx] = future.result()
                except Exception:
                    penalties[idx] = penalty()
                done_count += 1
                print(f"[Stage {stage}] Sample {idx} done ({done_count}/{batch_size})")

        WALL_SPICE_TIME += (time.time() - t_spice_start)
        return np.array(penalties, dtype=np.float32).reshape(-1, 1)

    return funct

# ==========================================
# Main Entry Point
# ==========================================
if __name__ == "__main__":
    NUM_RUNS = 1
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    save_keepout_artifacts(
        ROUTING_KEEP_OUT_MASK,
        ROUTING_PATHS,
        os.path.join(OUTPUT_DIR, f"routing_keepout_{GRID_N}x{GRID_N}"),
    )

    dim = GRID_N * GRID_N
    bounds_array = np.array([[-0.5, 0.5]] * dim, dtype=np.float32)
    initial_places = []

    p_init1 = generate_initial_place()
    save_place_csv(p_init1, os.path.join(OUTPUT_DIR, "initial_place_bottom.csv"))
    initial_places.append(place_to_x0(p_init1))
    initial_places.append(place_to_x0(p_init1))
    x0_stage1_np = np.vstack(initial_places).astype(np.float32)

    for run_idx in range(1, NUM_RUNS + 1):
        print(f"\n🚀 Starting two-stage tSS-BO ({GRID_N}x{GRID_N}) - Run {run_idx}...")
        WALL_SPICE_TIME = 0.0
        total_start_time = time.time()

        if os.path.exists(TMP_SPICE_DIR): shutil.rmtree(TMP_SPICE_DIR)
        os.makedirs(TMP_SPICE_DIR)

        pkl_stage1 = f"tssbo_stage1_{BENCHMARK.name}_Run{run_idx}.pkl"
        pkl_stage2 = f"tssbo_stage2_{BENCHMARK.name}_Run{run_idx}.pkl"

        # Stage 1: Coarse search
        main_solver(
            funct=create_tssbo_objective(stage=1, max_workers=SIM_MAX_WORKERS), dim=dim, bounds=bounds_array,
            init_x=x0_stage1_np,
            sigma=0.4, mu=0.5, batch_size=OPT_BATCH_SIZE, n_candidates=STAGE1_NMAX, nMax=STAGE1_NMAX, k=dim * 3,
            dataset_file=pkl_stage1
        )

        with open(pkl_stage1, "rb") as f:
            history1 = pickle.load(f)
        best_x_stage1_raw = history1[0].cpu().numpy()[np.argsort(history1[1].cpu().numpy().flatten())[:2]]
        x0_stage2_np = np.vstack(
            [place_to_x0(indices_to_place(decode_tsv_stage1(x))) for x in best_x_stage1_raw]).astype(np.float32)

        # Stage 2: Fine-tuning
        main_solver(
            funct=create_tssbo_objective(stage=2, max_workers=SIM_MAX_WORKERS), dim=dim, bounds=bounds_array,
            init_x=x0_stage2_np,
            sigma=0.5, batch_size=OPT_BATCH_SIZE, nMax=STAGE2_NMAX, k=dim * 3,
            dataset_file=pkl_stage2
        )

        with open(pkl_stage2, "rb") as f:
            history2_final = pickle.load(f)

        hist_y1, hist_x1 = history1[1].cpu().numpy().flatten(), history1[0].cpu().numpy()
        hist_y2, hist_x2 = history2_final[1].cpu().numpy().flatten(), history2_final[0].cpu().numpy()

        best_idx1, best_idx2 = np.argmin(hist_y1), np.argmin(hist_y2)

        if hist_y2[best_idx2] < hist_y1[best_idx1]:
            best_penalty_final, best_tsv_idx = hist_y2[best_idx2], decode_tsv_stage2(hist_x2[best_idx2])
            print("\n👑 Winner: Stage 2 (Fine-tuning achieved optimal electrical performance)")
        else:
            best_penalty_final, best_tsv_idx = hist_y1[best_idx1], decode_tsv_stage1(hist_x1[best_idx1])
            print("\n👑 Winner: Stage 1 (Electrical laws favor array clustering)")

        final_system_frequency = F_IDEAL_GHZ - best_penalty_final
        save_place_csv(indices_to_place(best_tsv_idx), os.path.join(OUTPUT_DIR, f"Run{run_idx}_best_place_tssbo.csv"))

        init_freq = run_spice_and_get_freq(p_init1, f"baseline_run{run_idx}") or 0.0

        total_minutes = (time.time() - total_start_time) / 60.0
        spice_minutes = WALL_SPICE_TIME / 60.0

        # ========================================================
        # Full History Generation and Saving Logic
        # ========================================================
        history_data = []
        global_best_penalty = float('inf')

        for val in hist_y1:
            if val < global_best_penalty: global_best_penalty = val
            history_data.append(
                ["Stage 1", 0.0 if val >= 10.0 else F_IDEAL_GHZ - val, max(0.0, F_IDEAL_GHZ - global_best_penalty)]
            )

        for val in hist_y2:
            if val < global_best_penalty: global_best_penalty = val
            history_data.append(
                ["Stage 2", 0.0 if val >= 10.0 else F_IDEAL_GHZ - val, max(0.0, F_IDEAL_GHZ - global_best_penalty)]
            )

        history_csv_name = f"{total_minutes:.2f}min_{BENCHMARK.name}_Run{run_idx}_tssbo_optimization_history.csv"

        pd.DataFrame(
            history_data,
            columns=["Optimization_Stage", "Current_Eval_Freq_GHz", "Historical_Best_Freq_GHz"]
        ).to_csv(os.path.join(OUTPUT_DIR, history_csv_name), index=False)
        print(f"[*] Convergence history saved: {os.path.join(OUTPUT_DIR, history_csv_name)}")

        print("\n" + "=" * 40)
        print(f"[+] Run {run_idx} completed! Current scale: {GRID_N}x{GRID_N}")
        print(f"[-] Baseline Freq: {init_freq:.4f} GHz | [+] Optimized Freq: {final_system_frequency:.4f} GHz")
        print(f"[*] Total Time: {total_minutes:.2f} mins")
        print("=" * 40 + "\n")
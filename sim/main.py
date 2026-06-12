import time
import os
import shutil
import uuid
import random
from functools import partial
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import numpy as np
import cma
import matplotlib.pyplot as plt

from em_simulation import em_simulation
import hspice_gpt
import hspice_gpt_end

SCALES = np.array([
    1e-10,  # L_AX
    1e-04,  # R_AX
    1e-14,  # C_psi
    1e-14,  # C_sub
    1e+2,  # R_sub
    1e-10,  # L_BX
    1e-4,  # R_BX
    1e-15,  # C_pgbx
    1e-10,  # L_CX
    1e+2  # R_CX
])


def real_params(x_scaled):
    return x_scaled * SCALES



def objective(x_scaled, hfss_freq, hfss_s12, net):

    work_dir = f"***"
    os.makedirs(work_dir, exist_ok=True)

    compare = 100000.0

    try:

        x = real_params(x_scaled)
        L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX = x

        spice_dir, flag = hspice_gpt.hspice_run(
            L_AX, R_AX, C_psi, C_sub, R_sub,
            L_BX, R_BX, C_pgbx, L_CX, R_CX,
            net, C_pgbx, C_pgbx, work_dir
        )

        if flag == 0:
            spice_file = os.path.join(spice_dir, "***")
            if os.path.exists(spice_file):

                res = pd.read_csv(spice_file, skiprows=1, header=None)
                col_res = res.iloc[:, 3].to_numpy()

                min_len = min(len(hfss_s12), len(col_res))

                if min_len < len(hfss_s12) * 0.8:
                    compare = 100000.0
                else:
                    f_GHz = hfss_freq[:min_len] / 1e9 if np.max(hfss_freq) > 1e6 else hfss_freq[:min_len]

                    weights = np.where(f_GHz > 20, 1.0, 1.0)

                    diff = np.abs(hfss_s12[:min_len] - col_res[:min_len])
                    weighted_diff = diff * weights

                    compare = float(np.sum(weighted_diff))
                    # print(f"[{os.getpid()}] Objective: {compare:.4f}")
    except Exception as e:
        print(f"[{os.getpid()}] run error: {e}")
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

    return compare


def extend_array(arr, length):
    if len(arr) < length:
        return np.concatenate([arr, np.full(length - len(arr), np.nan)])
    return arr


def plot_three_curves(HFSS_file, spice_before, spice_after):
    s12 = pd.read_csv(HFSS_file, skiprows=1, header=None)
    y_hfss = s12.iloc[:, 1]

    r1 = pd.read_csv(spice_before, skiprows=1, header=None)
    y_before = r1.iloc[:, 3]

    r2 = pd.read_csv(spice_after, skiprows=1, header=None)
    y_after = r2.iloc[:, 3]

    L = min(len(y_hfss), len(y_before), len(y_after))

    plt.figure(figsize=(10, 6))
    plt.plot(y_hfss.iloc[:L], label="HFSS", linewidth=2)
    plt.plot(y_before.iloc[:L], label="Before Optimization", linestyle='--')
    plt.plot(y_after.iloc[:L], label="After Optimization", linestyle='-.')
    plt.legend()
    plt.xlabel("Index")
    plt.ylabel("dB20(Z)")
    plt.title("HFSS vs Before vs After Optimization")
    plt.grid(True)
    plt.show()


if __name__ == "__main__":

    for exp_idx in range(2):
        print(f"\n{'=' * 50}")
        print(f"🚀 start {exp_idx + 1} ")
        print(f"{'=' * 50}\n")

        net = 23

        current_time = time.localtime()
        date = f"{current_time.tm_year % 100:02d}{current_time.tm_mon:02d}{current_time.tm_mday:02d}_{current_time.tm_hour:02d}{current_time.tm_min:02d}"
        experiment_index = date
        experiment_iter = str(exp_idx + 1)

        src_path = os.path.abspath(__file__)
        project_dir = os.path.dirname(src_path)
        s12_tmp_data_file = "***"

        sim_start_time = time.time()


        solution_condition, result_dir = em_simulation(
            project_dir, s12_tmp_data_file, experiment_index, experiment_iter, net
        )
        print(f"HFSS sim output : {result_dir}")

        HFSS_file = os.path.join(result_dir, "***")
        if not os.path.exists(HFSS_file):
            print(f"❌ error can not find: {HFSS_file}")
            continue


        s12_df = pd.read_csv(HFSS_file, skiprows=1, header=None)
        hfss_freq = s12_df.iloc[:, 0].to_numpy()
        hfss_s12 = s12_df.iloc[:, 1].to_numpy()

        x0 = [
            4.95631569e-10, 5.34964218e-05, 5.20222180e-14, 2.24424665e-14,
            4.41319447e+02, 4.64749737e-10, 3.25721540e-05, 1.60960234e-15,
            4.12865619e-10, 1.28259398e+02
        ]
        x0_scaled = np.array(x0) / SCALES
        sigma0 = 1.0

        es = cma.CMAEvolutionStrategy(
            x0_scaled, sigma0,
            {'bounds': [0, None], 'maxiter': 50, 'verb_disp': 1}
        )

        max_iters = 50


        objective_func = partial(objective, hfss_freq=hfss_freq, hfss_s12=hfss_s12, net=net)


        with ProcessPoolExecutor(max_workers=5) as pool:
            for gen in range(max_iters):
                if es.stop():
                    print("🏁 CMA-ES can stop。")
                    break

                print(f"\n---  {gen + 1} / {max_iters}  CMA  ---")

                xs = es.ask()

                results = list(pool.map(objective_func, xs))

                es.tell(xs, results)
                es.disp()

        best_x_scaled = es.result.xbest
        best_f = es.result.fbest
        best_x_real = real_params(best_x_scaled)

        print(f"\n🏆 best parm: {best_x_real}")
        print(f"📉 smallest compare: {best_f}")


        spice_dir = "***"
        L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgcx, L_CX, R_CX = best_x_real

        hspice_gpt_end.hspice_run(
            L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgcx, L_CX, R_CX,
            net, C_pgcx, C_pgcx
        )


        data_csv_path = os.path.join(result_dir, "***")
        if os.path.exists(data_csv_path):
            df_data = pd.read_csv(data_csv_path, header=None, sep='\t')
        else:
            df_data = pd.DataFrame()

        result_csv_path = os.path.join(spice_dir, "***")
        if os.path.exists(result_csv_path):
            df_res = pd.read_csv(result_csv_path)
            col5 = df_res.iloc[:, 3].to_numpy()
        else:
            col5 = np.array([])

        col3 = best_x_real
        col4 = np.full(len(col3), best_f)

        max_len = max(len(df_data), len(col3), len(col5))

        col1 = extend_array(
            df_data.iloc[:, 0].to_numpy() if not df_data.empty and df_data.shape[1] > 0 else np.array([]), max_len)
        col2 = extend_array(
            df_data.iloc[:, 1].to_numpy() if not df_data.empty and df_data.shape[1] > 1 else np.array([]), max_len)
        col3 = extend_array(col3, max_len)
        col4 = extend_array(col4, max_len)
        col5 = extend_array(col5, max_len)

        result_df = pd.DataFrame({
            'Parameter_Name': col1,
            'Parameter_Value': col2,
            'Best_X_Scaled': col3,
            'Best_F': col4,
            'Result_Col4': col5
        })

        output_path = os.path.join(result_dir, "***")
        result_df.to_csv(output_path, index=False)
        print(f"📁 the {exp_idx + 1} data saved to: {output_path}")
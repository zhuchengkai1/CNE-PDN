import os
import copy
import math
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import subprocess
import joblib


import hspice_gpt



def run_hspice_simulator(y_params_real, x_params_real, OUTPUT_DIR, output_prefix="tsv_simulation"):
    L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX = y_params_real
    net = int(x_params_real[6])

    out_dir, flag = hspice_gpt.hspice_run(
        L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx,
        L_CX, R_CX, net, C_pgbx, C_pgbx, OUTPUT_DIR
    )

    if flag == 1:
        print(f"[error] {OUTPUT_DIR} sim error")
        return None

    res_csv = os.path.join(out_dir, "***")
    if os.path.exists(res_csv):
        df_res = pd.read_csv(res_csv)

        z_mag_array = pd.to_numeric(df_res.iloc[:, -1], errors="coerce").dropna().values

        if len(z_mag_array) == 0:
            print(f"\n[warning] HSPICE output error！")
            return None

        return z_mag_array
    else:
        print(f"[error]")
        return None


def load_dataset_from_tmp(tmp_dir):
    X_list, y_list, z_true_list = [], [], []
    for folder in os.listdir(tmp_dir):
        csv_path = os.path.join(tmp_dir, folder, "***")
        if not os.path.exists(csv_path):
            continue

        df = pd.read_csv(csv_path)

        y = pd.to_numeric(df.iloc[0:10, 2], errors="coerce").values
        if len(y) != 10 or np.isnan(y).any() or np.any(y <= 0):
            continue

        X = pd.to_numeric(df.iloc[0:8, 1], errors="coerce").values
        if len(X) != 8 or np.isnan(X).any():
            continue

        z_col = pd.to_numeric(df.iloc[:, 4], errors="coerce").dropna().values
        if len(z_col) == 0:
            continue

        X_list.append(X.astype(np.float32))
        y_list.append(y.astype(np.float32))
        z_true_list.append(z_col)


    return np.array(X_list), np.array(y_list), np.array(z_true_list)



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


if __name__ == "__main__":
    EPS = 1e-20

    TRAIN_DIR = "train_data"
    TEST_DIR = "test_data"

    X_train, y_train, z_train = load_dataset_from_tmp(TRAIN_DIR)

    X_test, y_test, z_test = load_dataset_from_tmp(TEST_DIR)

    if len(X_train) == 0 or len(X_test) == 0:
        print("[Error] Training or Testing data not found. Please check folder paths.")
        exit(1)

    print(f"Data Loaded! Train samples: {len(X_train)}, Test samples: {len(X_test)}")

    y_train = np.log10(np.clip(y_train, EPS, None))
    y_test = np.log10(np.clip(y_test, EPS, None))


    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    X_train = torch.tensor(scaler_x.fit_transform(X_train), dtype=torch.float32)
    y_train = torch.tensor(scaler_y.fit_transform(y_train), dtype=torch.float32)

    X_test = torch.tensor(scaler_x.transform(X_test), dtype=torch.float32)
    y_test = torch.tensor(scaler_y.transform(y_test), dtype=torch.float32)

    model = TinyRobustMLP()
    criterion = nn.MSELoss()

    X_train = torch.tensor(scaler_x.fit_transform(X_train), dtype=torch.float32)
    y_train = torch.tensor(scaler_y.fit_transform(y_train), dtype=torch.float32)
    X_test = torch.tensor(scaler_x.transform(X_test), dtype=torch.float32)
    y_test = torch.tensor(scaler_y.transform(y_test), dtype=torch.float32)

    model = TinyRobustMLP()
    criterion = nn.MSELoss()

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=2000, eta_min=1e-5)

    for epoch in range(2000):
        model.train()
        pred_train = model(X_train)
        train_loss = criterion(pred_train, y_train)

        optimizer.zero_grad()
        train_loss.backward()
        optimizer.step()

        scheduler.step()

        model.eval()
        with torch.no_grad():
            pred_test = model(X_test)
            test_loss = criterion(pred_test, y_test)

        if epoch % 50 == 0:
            current_lr = scheduler.get_last_lr()[0]
            print(
                f"Epoch {epoch:4d} | LR: {current_lr:.2e} | Train Loss: {train_loss.item():.5e} | Test Loss: {test_loss.item():.5e}")

    print("✅ tran success！")


    model_save_path = "tiny_robust_mlp.pth"
    scaler_x_path = "scaler_x.pkl"
    scaler_y_path = "scaler_y.pkl"

    torch.save(model.state_dict(), model_save_path)
    joblib.dump(scaler_x, scaler_x_path)
    joblib.dump(scaler_y, scaler_y_path)

    print(f"💾 [save success] ！")


    model.eval()
    with torch.no_grad():
        pred_test_scaled = model(X_test)

    pred_test_log = scaler_y.inverse_transform(pred_test_scaled.cpu().numpy())
    y_test_log = scaler_y.inverse_transform(y_test.cpu().numpy())

    pred_test_real = np.power(10.0, pred_test_log)
    y_test_real = np.power(10.0, y_test_log)
    X_test_real = scaler_x.inverse_transform(X_test.cpu().numpy())

    rmse_each = np.sqrt(np.mean((pred_test_real - y_test_real) ** 2, axis=0))
    rel_err = np.mean(np.abs(pred_test_real - y_test_real) / (y_test_real + 1e-12))

    print("\n======== Robust MLP RLC Parameters Error ========")
    for i, v in enumerate(rmse_each):
        print(f"  Output {i:2d} (RLC): RMSE = {v:.3e}")
    print(f"  Mean Relative Error (RLC): {rel_err * 100:.2f}%")
    print("=================================================")


    test_set_size = len(z_test)
    print(f"\nStarting Point-by-Point SPICE Validation on ALL {test_set_size} test samples...")
    OUTPUT_DIR_PRED = os.path.join(os.getcwd(), "hspice_output_pred")

    best_rel_err = float('inf')
    best_sample_info = None

    for i in range(test_set_size):
        z_true_array = z_test[i]
        true_x_params = X_test_real[i]
        pred_y_params = pred_test_real[i]

        z_pred_array = run_hspice_simulator(pred_y_params, true_x_params, OUTPUT_DIR_PRED,
                                            output_prefix=f"tsv_eval_pred_{i}")

        if z_true_array is not None and z_pred_array is not None:
            min_len = min(len(z_true_array), len(z_pred_array))
            z_t = z_true_array[:min_len]
            z_p = z_pred_array[:min_len]

            rel_err_array = np.abs(z_p - z_t) / np.abs(z_t)
            mean_rel_err = np.mean(rel_err_array)

            mean_z_t = np.mean(z_t)
            mean_z_p = np.mean(z_p)

            print(
                f"Sample {i:3d} / {test_set_size - 1} | True Z(avg): {mean_z_t:8.4f} | Pred Z(avg): {mean_z_p:8.4f} | Full-Spectrum Rel Err: {mean_rel_err * 100:6.2f}%")

            if mean_rel_err < best_rel_err:
                best_rel_err = mean_rel_err
                best_sample_info = {
                    "index": i,
                    "true_z_avg": mean_z_t,
                    "pred_z_avg": mean_z_p,
                    "mean_abs_err": np.mean(np.abs(z_p - z_t)),
                    "rel_err": mean_rel_err,
                    "x_params": true_x_params,
                    "y_params_pred": pred_y_params
                }


    if best_sample_info is not None:
        print("\n" + "=" * 55)
        print("🏆  SPICE simulate (Lowest MAPE) 🏆")
        print("=" * 55)
        print(f"simble (Test Set Index) : {best_sample_info['index']}")
        print(f"average Z (Ground Truth Z_avg) : {best_sample_info['true_z_avg']:.4f} Ohms")
        print(f" (Predicted Z_avg)    : {best_sample_info['pred_z_avg']:.4f} Ohms")
        print(f" (Mean Abs Error) : {best_sample_info['mean_abs_err']:.4f} Ohms")
        print(f" (MAPE)         : {best_sample_info['rel_err'] * 100:.4f} %")
        print("-" * 55)
        print(" (Y_pred):")
        for idx, val in enumerate(best_sample_info['y_params_pred']):
            print(f"  Param {idx}: {val:.4e}")
        print("=" * 55 + "\n")
    else:
        print("\n[warning]  HSPICE ")
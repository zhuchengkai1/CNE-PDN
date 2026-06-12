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

import hspice_gpt



def build_y(v):
    v = v.clone()
    v[0] = v[0] * -1  # self-capacitance
    v[1:] = v[1:] * -0.5  # mutual-capacitance
    sum_c = torch.sum(v)
    v[0] = torch.abs(sum_c) * -1
    v = v * -1
    return v



def run_hspice_simulator(y_params_real, x_params_real, OUTPUT_DIR, output_prefix="tsv_simulation"):
    L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX = y_params_real
    net = int(x_params_real[6])

    out_dir, flag = hspice_gpt.hspice_run(
        L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx,
        L_CX, R_CX, net, C_pgbx, C_pgbx, OUTPUT_DIR
    )

    if flag == 1:
        print(f"[error] {OUTPUT_DIR} simulate error")
        return None

    res_csv = os.path.join(out_dir, "***")
    if os.path.exists(res_csv):
        df_res = pd.read_csv(res_csv)
        last_column_data = df_res.iloc[:, -1].values

        avg_z_mag = np.nanmean(last_column_data)

        if np.isnan(avg_z_mag):
            print(f"\n[warning] HSPICE output NaN！")
            return None

        return avg_z_mag
    else:
        print(f"[error] can not {out_dir} find result.csv。")
        return None



def load_dataset_from_tmp(tmp_dir):
    X_list, y_list, z_true_list = [], [], []

    if os.path.exists(tmp_dir):
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
            avg_z_true = np.mean(z_col)

            X_list.append(X.astype(np.float32))
            y_list.append(y.astype(np.float32))
            z_true_list.append(avg_z_true)

    return np.array(X_list), np.array(y_list), np.array(z_true_list)



class TinyRobustMLP_SingleOut(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(8, 32),
            nn.BatchNorm1d(32),
            nn.SiLU(),
            nn.Dropout(0.1),


            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.SiLU(),



            nn.Linear(16, 1)
        )

    def forward(self, x):
        return self.net(x)


if __name__ == "__main__":
    EPS = 1e-12
    X, y, z_true_all = load_dataset_from_tmp("tmp")

    if len(X) == 0:
        print("[Warn] No data found in 'tmp', generating random mock data...")
        X = np.random.rand(100, 8).astype(np.float32)
        y = np.random.rand(100, 10).astype(np.float32) * 100 + 1
        z_true_all = np.random.rand(100).astype(np.float32) * 50 + 20

    y = np.log10(np.clip(y, EPS, None))

    X_train, X_test, y_train, y_test, z_train, z_test = train_test_split(
        X, y, z_true_all, test_size=0.15, random_state=42
    )

    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    X_train = torch.tensor(scaler_x.fit_transform(X_train), dtype=torch.float32)
    y_train = torch.tensor(scaler_y.fit_transform(y_train), dtype=torch.float32)
    X_test = torch.tensor(scaler_x.transform(X_test), dtype=torch.float32)
    y_test = torch.tensor(scaler_y.transform(y_test), dtype=torch.float32)


    num_targets = 10
    models = [TinyRobustMLP_SingleOut() for _ in range(num_targets)]
    criterion = nn.MSELoss()

    optimizers = [torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-2) for m in models]
    schedulers = [torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=2000, eta_min=1e-5) for opt in optimizers]

    print(f"Starting Training for {num_targets} Independent MLPs (Full 2000 Epochs)...")

    for epoch in range(2000):
        total_train_loss = 0.0
        total_test_loss = 0.0

        for i in range(num_targets):
            models[i].train()

            target_y_train = y_train[:, i:i + 1]

            pred_train = models[i](X_train)
            loss = criterion(pred_train, target_y_train)

            optimizers[i].zero_grad()
            loss.backward()
            optimizers[i].step()
            schedulers[i].step()

            total_train_loss += loss.item()


            models[i].eval()
            with torch.no_grad():
                target_y_test = y_test[:, i:i + 1]
                pred_test = models[i](X_test)
                test_loss = criterion(pred_test, target_y_test)
                total_test_loss += test_loss.item()


        if epoch % 50 == 0:
            avg_train_loss = total_train_loss / num_targets
            avg_test_loss = total_test_loss / num_targets
            current_lr = schedulers[0].get_last_lr()[0]
            print(
                f"Epoch {epoch:4d} | LR: {current_lr:.2e} | Avg Train Loss: {avg_train_loss:.5e} | Avg Test Loss: {avg_test_loss:.5e}")

    print("✅ 10 network success！")


    pred_test_list = []


    for i in range(num_targets):
        models[i].eval()
        with torch.no_grad():
            pred_test_list.append(models[i](X_test))


    pred_test_scaled_combined = torch.cat(pred_test_list, dim=1)


    pred_test_log = scaler_y.inverse_transform(pred_test_scaled_combined.cpu().numpy())
    y_test_log = scaler_y.inverse_transform(y_test.cpu().numpy())

    pred_test_real = np.power(10.0, pred_test_log)
    y_test_real = np.power(10.0, y_test_log)
    X_test_real = scaler_x.inverse_transform(X_test.cpu().numpy())


    rmse_each = np.sqrt(np.mean((pred_test_real - y_test_real) ** 2, axis=0))
    rel_err = np.mean(np.abs(pred_test_real - y_test_real) / (y_test_real + 1e-12))

    print("\n======== Independent MLPs RLC Parameters Error ========")
    for i, v in enumerate(rmse_each):
        print(f"  Output {i:2d} (RLC): RMSE = {v:.3e}")
    print(f"  Mean Relative Error: {rel_err * 100:.2f}%")
    print("=======================================================")


    print("\nStarting SPICE Validation on a randomly selected test sample...")
    sample_idx = random.randint(0, len(z_test) - 1)

    avg_z_true = z_test[sample_idx]
    true_x_params = X_test_real[sample_idx]

    pred_y_params = pred_test_real[sample_idx]
    pred_y_params_new = copy.deepcopy(pred_y_params)


    pred_y_params_new[:4] = build_y(torch.tensor(pred_y_params_new[:4])).numpy()
    pred_y_params_new[5:8] = build_y(torch.tensor(pred_y_params_new[5:8])).numpy()

    OUTPUT_DIR_PRED = os.path.join(os.getcwd(), "hspice_output_pred")


    avg_z_pred = run_hspice_simulator(pred_y_params_new, true_x_params, OUTPUT_DIR_PRED, output_prefix="tsv_eval_pred")

    if avg_z_true is not None and avg_z_pred is not None:
        abs_err_z = abs(avg_z_pred - avg_z_true)
        rel_err_z = abs_err_z / avg_z_true

        print(f"\n======== SPICE Impedance Residual Analysis ========")
        print(f"Sample Index (Test Set): {sample_idx}")
        print(f"Ground Truth Avg Z: {avg_z_true:.4f} Ohms")
        print(f"Predicted Avg Z:    {avg_z_pred:.4f} Ohms")
        print(f"Absolute Z Error:   {abs_err_z:.4f} Ohms")
        print(f"Relative Z Error:   {rel_err_z * 100:.2f} %")
        print("====================================================\n")
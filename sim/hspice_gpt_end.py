import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
import numpy as np
import glob
import circuit_end
import csv

HSPICE_PATH = r"***"
SP_FILE = "***"
OUTPUT_DIR = "***"


if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"create output: {OUTPUT_DIR}")
else:
    print(f"output is save: {OUTPUT_DIR}")

    for file in glob.glob(os.path.join(OUTPUT_DIR, "inverter.*")):
        try:
            os.remove(file)
            print(f"delate old file: {file}")
        except Exception as e:
            print(f"delate {file} error: {e}")



def read_ac0_fixed_width(ac0_file, num_length=13):

    with open(ac0_file, 'r') as f:
        lines = f.readlines()

    print(f": {ac0_file}")
    print(f"{num_length} ")
    lines = lines[5:]
    numbers = []

    for line in lines:
        line = line.rstrip("\n")
        for i in range(0, len(line), 13):
            chunk = line[i:i + 13].strip()
            if chunk:
                numbers.append(chunk)

    rows = [numbers[i:i + 5] for i in range(0, len(numbers), 5)]
    output_csv = os.path.join(OUTPUT_DIR, "***")

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def data_deal(my_file):
    df = pd.read_csv(my_file, header=None,
                     names=['freq', 'V_re', 'V_im', 'I_re', 'I_im'])

    V = df['V_re'].to_numpy() + 1j * df['V_im'].to_numpy()
    I = df['I_re'].to_numpy() + 1j * df['I_im'].to_numpy()

    I_safe = I.copy()
    I_safe[np.abs(I_safe) < 1e-30] = 1e-30

    Z = V / I_safe
    Z_mag = np.abs(Z)
    Z_dB20 = 20 * np.log10(Z_mag + 1e-30)

    df_out = pd.DataFrame({
        'freq': df['freq'],
        'Z_re': np.real(Z),
        'Z_im': np.imag(Z),
        'Z_mag': Z_dB20,
        'Z_phase_deg': np.angle(Z, deg=True)
    })

    output_csv = os.path.join(OUTPUT_DIR, "***")
    df_out.to_csv(output_csv, index=False)


def plot_ac_response(df, node_name="node_1_1"):

    if df.empty:
        print("error")
        return

    mag_min, mag_max = df["Mag"].min(), df["Mag"].max()

    print(f"from: {mag_min:.2e} to {mag_max:.2e}")

    if mag_max < 1e-10:
        df["Mag_dB"] = 20 * np.log10(np.maximum(df["Mag"], 1e-100))

        fig, ax1 = plt.subplots(1, 1, figsize=(10, 4))

        ax1.semilogx(df["Freq(Hz)"], df["Mag_dB"], 'b-', linewidth=2)
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Magnitude (dB)")
        ax1.grid(True, which="both", ls="--", alpha=0.7)
        ax1.set_title(f"AC Magnitude Response at {node_name} (dB)")

        plt.show()

    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(5, 8))

        ax1.loglog(df["Freq(Hz)"], df["Mag"], 'b-', linewidth=2)
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Magnitude |V|")
        ax1.grid(True, which="both", ls="--", alpha=0.7)
        ax1.set_title(f"AC Magnitude Response at {node_name}")

        plt.show()



def hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgcx, L_CX, R_CX, net, C_pgax, C_pgbx):
    circuit_end.example_usage(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, net, C_pgbx, C_pgbx)

    print(" HSPICE sim...")
    print(f"SP file: {SP_FILE}")
    print(f"HSPICE road: {HSPICE_PATH}")

    if not os.path.exists(SP_FILE):
        print(f"error: SP file {SP_FILE} can not find!")
        exit(1)

    try:
        result = subprocess.run([HSPICE_PATH, SP_FILE],
                                capture_output=True,
                                text=True,
                                shell=True)

        print(f"HSPICE feed back: {result.returncode}")

        if result.returncode == 0:
            print("HSPICE sim success!")
        else:
            print(f"HSPICE failed，feed back: {result.returncode}")
            if result.stderr:
                print(f"error: {result.stderr}")

    except Exception as e:
        print(f"HSPICE error: {e}")
        exit(1)


    files_moved = 0
    for file in os.listdir("."):
        if file.startswith("inverter.") or file.startswith("inverter.sp#"):
            try:
                shutil.move(file, os.path.join(OUTPUT_DIR, file))
                files_moved+=1
                print(f"move file: {file}")
            except Exception as e:
                print(f"move {file} error: {e}")
    print(f"move {files_moved} files to {OUTPUT_DIR}")
    AC0_FILE = os.path.join(OUTPUT_DIR, "***")
    my_file = os.path.join(OUTPUT_DIR, "***")
    if not os.path.exists(AC0_FILE):

        return

    print(f"find AC output file: {AC0_FILE}")


    read_ac0_fixed_width(AC0_FILE, num_length=13)
    data_deal(my_file)
    return OUTPUT_DIR



if __name__ == "__main__":
    L_AX = 2e-10
    L_BX = 1.5e-10
    L_CX = 7e-10
    R_AX = 0.1
    R_BX = 0.1
    R_CX = 0.1
    C_psi = 1e-15
    C_sub = 1e-15
    C_pgax = C_pgbx = C_pgcx = 1e-15
    R_sub = 0.1
    net = 11
    output_dir = hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, net, C_pgbx, C_pgbx)
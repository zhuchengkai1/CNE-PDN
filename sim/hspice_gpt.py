import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
import numpy as np
import glob
import circuit
import csv

HSPICE_PATH = r"***"

SP_FILE = f"***"



def read_ac0_fixed_width(ac0_file, OUTPUT_DIR,num_length=13):

    with open(ac0_file, 'r') as f:
        lines = f.readlines()

    print(f" {ac0_file}")
    print(f" {num_length} ")
    lines = lines[5:]
    numbers = []

    for line in lines:
        line = line.rstrip("\n")

        for i in range(0, len(line), 13):
            chunk = line[i:i + 13].strip()
            if chunk:
                numbers.append(chunk)


    rows = [numbers[i:i + 5] for i in range(0, len(numbers), 5)]
    output_csv = os.path.join(OUTPUT_DIR, "my.csv")

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def data_deal(my_file,OUTPUT_DIR):
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
        print("error:no data")
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


def hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgcx, L_CX, R_CX, net, C_pgax, C_pgbx,OUTPUT_DIR):
    flag = 0
    circuit.example_usage(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, net, C_pgbx, C_pgbx,SP_FILE)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"create output file: {OUTPUT_DIR}")
    else:
        print(f"output file: {OUTPUT_DIR}")
        for file in glob.glob(os.path.join(OUTPUT_DIR, "inverter.*")):
            try:
                os.remove(file)
                print(f"delate old file: {file}")
            except Exception as e:
                print(f"delate file {file} error: {e}")



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
            print(f"HSPICE error，: {result.returncode}")
            if result.stderr:
                print(f"error: {result.stderr}")

    except Exception as e:
        print(f"HSPICE run error: {e}")
        exit(1)

    sp_prefix = os.path.splitext(SP_FILE)[0]

    files_moved = 0

    for file in os.listdir("."):
        if file.startswith(sp_prefix):
            try:
                shutil.move(file, os.path.join(OUTPUT_DIR, file))
                files_moved += 1
                print(f"move file: {file}")
            except Exception as e:
                print(f"move {file} error: {e}")

    print(f"move {files_moved} files to {OUTPUT_DIR}")

    AC0_FILE = os.path.join(OUTPUT_DIR, f"{sp_prefix}.ac0")
    my_file = os.path.join(OUTPUT_DIR, "my.csv")

    if not os.path.exists(AC0_FILE):
        flag = 1

        return OUTPUT_DIR, flag

    print(f"find ac file: {AC0_FILE}")

    read_ac0_fixed_width(AC0_FILE, OUTPUT_DIR, num_length=13)
    data_deal(my_file, OUTPUT_DIR)
    return OUTPUT_DIR, flag



if __name__ == "__main__":
    # L_AX = 1.0127762416544806e-09
    # R_AX = 0.0011753546649631887
    # C_psi = 4.8193800723322945e-14
    # C_sub = 8.421198446923972e-14
    # R_sub = 247.361029693644
    # L_BX = 9.032549448059374e-10
    # R_BX = 0.0002374202318445426
    # C_pgax = C_pgbx = C_pgcx =3.632994446271597e-15
    # L_CX = 1.0767791133699507e-10
    # R_CX = 416.12075635077804
    #
    # net = 23
    # L_AX = 6.276232e-10
    # R_AX = 1.156018e-04
    # C_psi = 3.347578e-14
    # C_sub = 9.212883e-15
    # R_sub = 4.084614e+02
    # L_BX = 6.783313e-10
    # R_BX = 5.955472e-05
    # C_pgcx= C_pgax=C_pgbx = 1.068626e-15
    # L_CX = 4.531783e-10
    # R_CX = 1.752872e+02
    # net=10
    L_AX = 2.410e-07
    R_AX = 2.513e-02
    C_pgax = 1.030e-21
    C_psi = 6.070e-09
    C_sub = 2.109e-10
    C_gsi = 6.070e-09
    R_sub = 4.996e-02
    L_BX = 3.135e-07
    R_BX = 1.377e-01
    C_pgbx = 1.030e-21
    L_CX = 6.270e-07
    R_CX = 5.000e-02
    C_pgcx = 1.030e-21
    net =10
    output_dir_name = "***"

    print(f"🚀 start HSPICE sim ( net={net})...")

    output_dir, flag = hspice_run(
        L_AX, R_AX, C_psi, C_sub, R_sub,
        L_BX, R_BX, C_pgcx, L_CX, R_CX,
        net, C_pgax, C_pgbx, output_dir_name
    )

    if flag == 0:
        result_csv_path = os.path.join(output_dir, "result.csv")
        if os.path.exists(result_csv_path):
            print(f"\n✅ sim success: {result_csv_path}")

            df_res = pd.read_csv(result_csv_path)

            freqs = df_res['freq']
            z_mag_db = df_res['Z_mag']

            plt.figure(figsize=(8, 5))
            plt.semilogx(freqs, z_mag_db, 'b-', linewidth=2, label='Transfer Impedance Z(dB20)')
            plt.xlabel("Frequency (Hz)", fontsize=12)
            plt.ylabel("Magnitude (dB20)", fontsize=12)
            plt.title(f"HSPICE Transfer Impedance Profile (net={net})", fontsize=14)
            plt.grid(True, which="both", ls="--", alpha=0.7)
            plt.legend(fontsize=12)
            plt.tight_layout()
            plt.show()

        else:
            print(f"\n❌ can not find file: {result_csv_path}")
    else:
        print("\n❌ HSPICE sim failed")
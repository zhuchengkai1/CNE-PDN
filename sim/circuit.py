def example_usage(L_AX,R_AX,C_psi,C_sub,R_sub,L_BX,R_BX,C_pgbx,L_CX,R_CX,net,C_pgcx,C_pgax,sp_filename):

    spice_content = """

.TITLE son

.option post=2 probe
.option numdgt=6
.option brief

"""
    spice_content = spice_content + ".PARAM \n+ L_AX = " + str(L_AX) + "\n+ R_AX = " + str(R_AX) + "\n+ C_psi = " + str(C_psi) + "\n+ C_sub = " + str(C_sub) + "\n+ R_sub = " + str(R_sub) + "\n+ L_BX = " + str(L_BX) + "\n+ R_BX = " + str(R_BX) + "\n+ C_pgbx = " + str(C_pgbx) + "\n+ L_CX = " + str(L_CX) + "\n+ R_CX = " + str(R_CX) + "\n+ C_pgax = " + str(C_pgax)+ "\n+ C_pgcx = " + str(C_pgcx)
    son = """ 
    
.SUBCKT MY_CIRCUIT_1 in2 down in1 right  a gnd
L_AX1 N014 N013  L_AX 
R_AX1 N015 N014  R_AX 
C_pgax1 N015 gnd  C_pgax 
C_psi1 N015 N024  C_psi 
C1 N024 N026  C_sub 
C2 N026 gnd  C_psi 
R1 N024 N026  R_sub 
L_BX1 N016 N015  L_BX 
R_bx1 N017 N016  R_BX 
C_pgbx1 N017 gnd  C_pgbx 
L_CX1 N018 N017  L_CX 
R_CX1 a N018  R_CX 
C_pgcx1 a gnd  C_pgbx 
V1 N013 in1 AC 1
C_psi2 N017 N027  C_psi 
C3 N027 N032  C_sub 
C4 N032 gnd  C_psi 
R2 N027 N032  R_sub 
C_psi3 a N030  C_psi 
C5 N030 N034  C_sub 
C6 N034 gnd  C_psi 
R3 N030 N034  R_sub 
L_CX2 N019 a  L_CX 
R_CX2 N020 N019  R_CX 
C_pgcx2 N020 gnd  C_pgbx 
C_psi4 N020 N031  C_psi 
C7 N031 N035  C_sub 
C8 N035 gnd  C_psi 
R4 N031 N035  R_sub 
L_BX2 N021 N020  L_BX 
R_bx2 N022 N021  R_BX 
C_pgbx2 N022 gnd  C_pgbx 
C_psi5 N022 N028  C_psi 
C9 N028 N033  C_sub 
C10 N033 gnd  C_psi 
R5 N028 N033  R_sub 
L_AX2 N023 N022  L_AX 
R_AX2 right N023  R_AX 
C_pgax2 right gnd  C_pgax 
C_psi6 right N025  C_psi 
C11 N025 N029  C_sub 
C12 N029 gnd  C_psi 
R6 N025 N029  R_sub 
L_AX3 N002 N001  L_AX 
R_AX3 N003 N002  R_AX 
C_pgax3 N003 gnd  C_pgax 
C_psi7 N003 N005  C_psi 
C13 N005 N004  C_sub 
C14 N004 gnd  C_psi 
R7 N005 N004  R_sub 
L_BX3 N006 N003  L_BX 
R_bx3 N007 N006  R_BX 
C_pgbx3 N007 gnd  C_pgbx 
L_CX3 N010 N007  L_CX 
R_CX3 a N010  R_CX 
C_pgcx3 a gnd  C_pgbx 
V2 N001 in2 AC 1
C_psi8 N007 N009  C_psi 
C15 N009 N008  C_sub 
C16 N008 gnd  C_psi 
R8 N009 N008  R_sub 
C_psi9 a N012  C_psi 
C17 N012 N011  C_sub 
C18 N011 gnd  C_psi 
R9 N012 N011  R_sub 
L_CX4 N036 a  L_CX 
R_CX4 N037 N036  R_CX 
C_pgcx4 N037 gnd  C_pgbx 
C_psi10 N037 N039  C_psi 
C19 N039 N038  C_sub 
C20 N038 gnd  C_psi 
R10 N039 N038  R_sub 
L_BX4 N040 N037  L_BX 
R_bx4 N041 N040  R_BX 
C_pgbx4 N041 gnd  C_pgbx 
C_psi11 N041 N043  C_psi 
C21 N043 N042  C_sub 
C22 N042 gnd  C_psi 
R11 N043 N042  R_sub 
L_AX4 N044 N041  L_AX 
R_AX4 down N044  R_AX 
C_pgax4 down gnd  C_pgax 
C_psi12 down N046  C_psi 
C23 N046 N045  C_sub 
C24 N045 gnd  C_psi 
R12 N046 N045  R_sub 
.ENDS MY_CIRCUIT_1


.SUBCKT MY_CIRCUIT_2 in down left right  a gnd
L_AX1 N013 left  L_AX 
R_AX1 N014 N013  R_AX 
C_pgax1 N014 gnd  C_pgax 
C_psi1 N014 N023  C_psi 
C1 N023 N025  C_sub 
C2 N025 gnd  C_psi 
R1 N023 N025  R_sub 
L_BX1 N015 N014  L_BX 
R_bx1 N016 N015  R_BX 
C_pgbx1 N016 gnd  C_pgbx 
L_CX1 N017 N016  L_CX 
R_CX1 a N017  R_CX 
C_pgcx1 a gnd  C_pgbx 
C_psi2 N016 N026  C_psi 
C3 N026 N031  C_sub 
C4 N031 gnd  C_psi 
R2 N026 N031  R_sub 
C_psi3 a N029  C_psi 
C5 N029 N033  C_sub 
C6 N033 gnd  C_psi 
R3 N029 N033  R_sub 
L_CX2 N018 a  L_CX 
R_CX2 N019 N018  R_CX 
C_pgcx2 N019 gnd  C_pgbx 
C_psi4 N019 N030  C_psi 
C7 N030 N034  C_sub 
C8 N034 gnd  C_psi 
R4 N030 N034  R_sub 
L_BX2 N020 N019  L_BX 
R_bx2 N021 N020  R_BX 
C_pgbx2 N021 gnd  C_pgbx 
C_psi5 N021 N027  C_psi 
C9 N027 N032  C_sub 
C10 N032 gnd  C_psi 
R5 N027 N032  R_sub 
L_AX2 N022 N021  L_AX 
R_AX2 right N022  R_AX 
C_pgax2 right gnd  C_pgax 
C_psi6 right N024  C_psi 
C11 N024 N028  C_sub 
C12 N028 gnd  C_psi 
R6 N024 N028  R_sub 
L_AX3 N002 N001  L_AX 
R_AX3 N003 N002  R_AX 
C_pgax3 N003 gnd  C_pgax 
C_psi7 N003 N005  C_psi 
C13 N005 N004  C_sub 
C14 N004 gnd  C_psi 
R7 N005 N004  R_sub 
L_BX3 N006 N003  L_BX 
R_bx3 N007 N006  R_BX 
C_pgbx3 N007 gnd  C_pgbx 
L_CX3 N010 N007  L_CX 
R_CX3 a N010  R_CX 
C_pgcx3 a gnd  C_pgbx 
V1 N001 in AC 1
C_psi8 N007 N009  C_psi 
C15 N009 N008  C_sub 
C16 N008 gnd  C_psi 
R8 N009 N008  R_sub 
C_psi9 a N012  C_psi 
C17 N012 N011  C_sub 
C18 N011 gnd  C_psi 
R9 N012 N011  R_sub 
L_CX4 N035 a  L_CX 
R_CX4 N036 N035  R_CX 
C_pgcx4 N036 gnd  C_pgbx 
C_psi10 N036 N038  C_psi 
C19 N038 N037  C_sub 
C20 N037 gnd  C_psi 
R10 N038 N037  R_sub 
L_BX4 N039 N036  L_BX 
R_bx4 N040 N039  R_BX 
C_pgbx4 N040 gnd  C_pgbx 
C_psi11 N040 N042  C_psi 
C21 N042 N041  C_sub 
C22 N041 gnd  C_psi 
R11 N042 N041  R_sub 
L_AX4 N043 N040  L_AX 
R_AX4 down N043  R_AX 
C_pgax4 down gnd  C_pgax
C_psi12 down N045  C_psi 
C23 N045 N044  C_sub 
C24 N044 gnd  C_psi 
R12 N045 N044  R_sub 

.ENDS MY_CIRCUIT_2


.SUBCKT MY_CIRCUIT_3 top down in right a gnd
L_AX1 N013 N012  L_AX 
R_AX1 N014 N013  R_AX 
C_pgax1 N014 gnd  C_pgax 
C_psi1 N014 N022  C_psi 
C1 N022 N024  C_sub 
C2 N024 gnd  C_psi 
R1 N022 N024  R_sub 
L_BX1 N015 N014  L_BX 
R_bx1 f N015  R_BX 
C_pgbx1 f gnd  C_pgbx 
L_CX1 N016 f  L_CX 
R_CX1 a N016  R_CX 
C_pgcx1 a gnd  C_pgbx 
V1 N012 in AC 1
C_psi2 f N025  C_psi 
C3 N025 N030  C_sub 
C4 N030 gnd  C_psi 
R2 N025 N030  R_sub 
C_psi3 a N028  C_psi 
C5 N028 N032  C_sub 
C6 N032 gnd  C_psi 
R3 N028 N032  R_sub 
L_CX2 N017 a  L_CX 
R_CX2 N018 N017  R_CX 
C_pgcx2 N018 gnd  C_pgbx 
C_psi4 N018 N029  C_psi 
C7 N029 N033  C_sub 
C8 N033 gnd  C_psi 
R4 N029 N033  R_sub 
L_BX2 N019 N018  L_BX 
R_bx2 N020 N019  R_BX 
C_pgbx2 N020 gnd  C_pgbx 
C_psi5 N020 N026  C_psi 
C9 N026 N031  C_sub 
C10 N031 gnd  C_psi 
R5 N026 N031  R_sub 
L_AX2 N021 N020  L_AX 
R_AX2 right N021  R_AX 
C_pgax2 right gnd  C_pgax 
C_psi6 right N023  C_psi 
C11 N023 N027  C_sub 
C12 N027 gnd  C_psi 
R6 N023 N027  R_sub 
L_AX3 N001 top  L_AX 
R_AX3 N002 N001  R_AX 
C_pgax3 N002 gnd  C_pgax 
C_psi7 N002 N004  C_psi 
C13 N004 N003  C_sub 
C14 N003 gnd  C_psi 
R7 N004 N003  R_sub 
L_BX3 N005 N002  L_BX 
R_bx3 N006 N005  R_BX 
C_pgbx3 N006 gnd  C_pgbx 
L_CX3 N009 N006  L_CX 
R_CX3 a N009  R_CX 
C_pgcx3 a gnd  C_pgbx 
C_psi8 N006 N008  C_psi 
C15 N008 N007  C_sub 
C16 N007 gnd  C_psi 
R8 N008 N007  R_sub 
C_psi9 a N011  C_psi 
C17 N011 N010  C_sub 
C18 N010 gnd  C_psi 
R9 N011 N010  R_sub 
L_CX4 N034 a  L_CX 
R_CX4 N035 N034  R_CX 
C_pgcx4 N035 gnd  C_pgbx 
C_psi10 N035 N037  C_psi 
C19 N037 N036  C_sub 
C20 N036 gnd  C_psi 
R10 N037 N036  R_sub 
L_BX4 N038 N035  L_BX 
R_bx4 N039 N038  R_BX 
C_pgbx4 N039 gnd  C_pgbx 
C_psi11 N039 N041  C_psi 
C21 N041 N040  C_sub 
C22 N040 gnd  C_psi 
R11 N041 N040  R_sub 
L_AX4 N042 N039  L_AX 
R_AX4 down N042  R_AX 
C_pgax4 down gnd  C_pgax 
C_psi12 down N044  C_psi 
C23 N044 N043  C_sub 
C24 N043 gnd  C_psi 
R12 N044 N043  R_sub 
.ENDS MY_CIRCUIT3


.SUBCKT MY_CIRCUIT_4 top down left right a gnd
L_AX1 N012 left  L_AX 
R_AX1 N013 N012  R_AX 
C_pgax1 N013 gnd  C_pgax 
C_psi1 N013 N022  C_psi 
C1 N022 N024  C_sub 
C2 N024 gnd  C_psi 
R1 N022 N024  R_sub 
L_BX1 N014 N013  L_BX 
R_bx1 N015 N014  R_BX 
C_pgbx1 N015 gnd  C_pgbx 
L_CX1 N016 N015  L_CX 
R_CX1 a N016  R_CX 
C_pgcx1 a gnd  C_pgbx 
C_psi2 N015 N025  C_psi 
C3 N025 N030  C_sub 
C4 N030 gnd  C_psi 
R2 N025 N030  R_sub 
C_psi3 a N028  C_psi 
C5 N028 N032  C_sub 
C6 N032 gnd  C_psi 
R3 N028 N032  R_sub 
L_CX2 N017 a  L_CX 
R_CX2 N018 N017  R_CX 
C_pgcx2 N018 gnd  C_pgbx 
C_psi4 N018 N029  C_psi 
C7 N029 N033  C_sub 
C8 N033 gnd  C_psi 
R4 N029 N033  R_sub 
L_BX2 N019 N018  L_BX 
R_bx2 N020 N019  R_BX 
C_pgbx2 N020 gnd  C_pgbx 
C_psi5 N020 N026  C_psi 
C9 N026 N031  C_sub 
C10 N031 gnd  C_psi 
R5 N026 N031  R_sub 
L_AX2 N021 N020  L_AX 
R_AX2 right N021  R_AX 
C_pgax2 right gnd  C_pgax 
C_psi6 right N023  C_psi 
C11 N023 N027  C_sub 
C12 N027 gnd  C_psi 
R6 N023 N027  R_sub 
L_AX3 N001 top  L_AX 
R_AX3 N002 N001  R_AX 
C_pgax3 N002 gnd  C_pgax 
C_psi7 N002 N004  C_psi 
C13 N004 N003  C_sub 
C14 N003 gnd  C_psi 
R7 N004 N003  R_sub 
L_BX3 N005 N002  L_BX 
R_bx3 N006 N005  R_BX 
C_pgbx3 N006 gnd  C_pgbx 
L_CX3 N009 N006  L_CX 
R_CX3 a N009  R_CX 
C_pgcx3 a gnd  C_pgbx 
C_psi8 N006 N008  C_psi 
C15 N008 N007  C_sub 
C16 N007 gnd  C_psi 
R8 N008 N007  R_sub 
C_psi9 a N011  C_psi 
C17 N011 N010  C_sub 
C18 N010 gnd  C_psi 
R9 N011 N010  R_sub 
L_CX4 N034 a  L_CX 
R_CX4 N035 N034  R_CX 
C_pgcx4 N035 gnd  C_pgbx 
C_psi10 N035 N037  C_psi 
C19 N037 N036  C_sub 
C20 N036 gnd  C_psi 
R10 N037 N036  R_sub 
L_BX4 N038 N035  L_BX 
R_bx4 N039 N038  R_BX 
C_pgbx4 N039 gnd  C_pgbx 
C_psi11 N039 N041  C_psi 
C21 N041 N040  C_sub 
C22 N040 gnd  C_psi 
R11 N041 N040  R_sub 
L_AX4 N042 N039  L_AX 
R_AX4 down N042  R_AX 
C_pgax4 down gnd  C_pgax 
C_psi12 down N044  C_psi 
C23 N044 N043  C_sub 
C24 N043 gnd  C_psi 
R12 N044 N043  R_sub 
.ENDS MY_CIRCUIT_4

"""
    spice_content = spice_content + son
    for i in range(net):
        for j in range(net):
            if i == 0 and j == 0:
                n = 0
                X11 = f"\nX_{i+1}_{j+1} input{n} con_{i*2+2}_{j+1} input{n + 1} con_{i*2+1}_{j+1} node_{i+1}_{j+1} 0 MY_CIRCUIT_1"
                n = n + 2
                spice_content = spice_content +X11
            elif i != 0 and j == 0:
                X12 = f"\nX_{i+1}_{j+1} con_{i*2}_{j+1} con_{i*2+2}_{j+1} input{n} con_{i*2+1}_{j+1} node_{i+1}_{j+1} 0 MY_CIRCUIT_3"
                spice_content = spice_content + X12
                n = n + 1
            elif i == 0 and j != 0:
                X21 = f"\nX_{i+1}_{j+1} input{n} con_{i*2+2}_{j+1} con_{i*2+1}_{j} con_{i*2+1}_{j+1} node_{i+1}_{j+1} 0 MY_CIRCUIT_2"
                spice_content = spice_content + X21
                n = n + 1
            else:
                X22 = f"\nX_{i + 1}_{j + 1} con_{i*2}_{j+1} con_{i * 2 + 2}_{j + 1} con_{i * 2 + 1}_{j} con_{i * 2 + 1}_{j+1} node_{i + 1}_{j + 1} 0 MY_CIRCUIT_4"
                spice_content = spice_content + X22

    for k in range(n):
        power = f"\nVin{k} input{k} 0 AC 1"
        spice_content = spice_content + power
    fre = "\n.ac lin 100 0.001G 50G"
    spice_content = spice_content + fre

    ac = f"\n.probe ac v(con_{1}_{net})\n.probe ac i(Vin1)"
    spice_content = spice_content + ac

    with open(sp_filename, 'w') as f:
        f.write(spice_content)
    print("create file: inverter.sp")


L_AX = 2.410e-07,
R_AX= 2.513e-02,
C_pgax=1.030e-21,
C_psi=6.070e-09,
C_sub= 2.109e-10,
R_sub= 4.996e-02,
L_BX= 3.135e-07,
R_BX= 1.377e-01,
C_pgbx= 1.030e-21,
L_CX= 6.270e-07,
R_CX= 5.000e-02,
C_pgcx= 1.030e-21
net = 10
# example_usage(L_AX,R_AX,C_psi,C_sub,R_sub,L_BX,R_BX,C_pgbx,L_CX,R_CX,net,C_pgbx,C_pgbx)
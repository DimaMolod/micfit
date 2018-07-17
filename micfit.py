#!/usr/bin/python
from subprocess import call
import subprocess
import sys
from Bio.PDB import PDBParser
import os
import numpy as np
from multiprocessing import Process
import time
start = time.time()

back = True

def pack_micelle(a, bc, length, number, pdbname, headatom, tailatom):
    par = "#\n#Input file for packmol, automatically generated by micfit\n#\n"
    par += "tolerance 2.0\n"
    par += "structure " + pdbname + "\n"
    par += "  number " + str(number) + "\n"
    par += "  atoms " + str(tailatom) + "\n"
    a1 = str(round(a-length,1)) + " "
    a2 = str(round(a,1)) + " "
    bc1 = str(round(bc-length,1)) + " "
    bc2 = str(round(bc,1)) + " "
    #d=4/3pi*a*b*c??

    par += "    inside ellipsoid 0. 0. 0. " + a1 + bc1 + bc1 + "0.0"
    par += "\n  end atoms\n"
    par += "  atoms " + str(headatom) + "\n"
    par += "    outside ellipsoid 0. 0. 0. " + a2 + bc2 + bc2 + "0.0"
    par += "\n  end atoms\n"
    par += "end structure\n\n"
    out = "micfit"+str(a)+str(bc)+str(number)+".pdb"
    par += "output " + out + "\n"
    with open("test.inp", "w") as text_file:
        text_file.write(par)
    os.system("packmol < test.inp")
    print(par)
    return out



def micfit(datfile, pdbfile):
    P = PDBParser(PERMISSIVE=1)
    s = P.get_structure(pdbfile, pdbfile)
    atoms = s.get_atoms()
    # Molecular weight
    mow = 0
    maxdist = 0
    try:
        for atom in atoms:
            for atom2 in atoms:
                mow += (atom2.mass)
                d = atom2 - atom
                if d > maxdist:
                    maxdist = d
                    a1 = atom
                    a2 = atom2
    except KeyError as e:
        print (e)
        print("Wrong format of PDB!")
    o = subprocess.Popen(['autorg',datfile], stdout=subprocess.PIPE)
    output = o.stdout.read()
    Rg = float(output.split(" ")[6])

    o = subprocess.Popen(['datgnom','-r', str(Rg), datfile], stdout=subprocess.PIPE)
    output = o.stdout.read()
    lines = output.split("\n")
    #print lines[8]
    blabla, Dmax = lines[8].split("size:")
    Dmax = float(Dmax.strip())
    #print lines[35]
    blabla, Rg_direct = lines[35].split("Rg:")
    Rg_direct = float(Rg_direct.strip())
    #print lines[36]
    blabla, I0 = lines[36].split("I(0):")
    I0 = float(I0.strip())
    o = subprocess.Popen(['datmw', datfile, '--rg', str(Rg), '--i0', str(I0)], stdout=subprocess.PIPE)
    output = o.stdout.read()
    mowmi = float(output.split(" ")[4])
    print ("Gyration radius of the micelle: " + str(Rg))
    print("Molecuar weight of the micelle: " + str(mowmi))
    print ("MW of a single molecule is: " + str(mow))
    #now we have all the parameters -- call packmol (mulithreading)
    print("--------------------------------------------------------------------")
    print("Parameters for the micelle model are:")
    print("Radius of the sphere: " + str(Dmax/2.0))
    print("Length of a single molecule: " + str(maxdist))
    print("Number of molecules: " + str(int(mowmi/mow)))
    print("Hydrophilic atom id: " + str(a1.serial_number))
    print("Hydrophobic atom id: " + str(a2.serial_number))
    le = maxdist
    aa1 = a1.serial_number
    aa2 = a2.serial_number
    os.system("rm micfit.pdb")
    wtf = raw_input("Run packmol with these parameters?(y/n) ")
    if wtf == "y" or wtf == "yes":
        rad = Dmax/2.0
        nmb = int(mowmi/mow)
        name = pack_micelle(rad, rad, float(le), nmb, pdbfile, int(aa1), int(aa2))
        call(["pymol", name])
        os.system("rm *.fit")
        os.system("rm *.log")
        os.system("rm *.sav")
        os.system("rm *.abs")
        os.system("rm *.alm")
        os.system("rm *.flm")
        os.system("crysol " + name + " " + datfile)
        os.system("primus *.fit")
        exit()
    if wtf == "n" or wtf == "no":
        amin = float(raw_input("Please enter lower value for the first semiaxis: "))
        amax = float(raw_input("Please enter upper value for the first semiaxis: "))
        astep = float(raw_input("Please enter a step: "))
        ar = np.arange(amin, amax+1, astep)
        print("grid: a= " + str(ar))
        bcmin = float(raw_input("Please enter lower value for the second and third semiaxes: "))
        bcmax = float(raw_input("Please enter upper value for the second and third semiaxes: "))
        bcstep = float(raw_input("Please enter a step: "))
        bcr = np.arange(bcmin, bcmax+1, bcstep)
        print("grid: b and c = " + str(bcr))
        nummin = int(raw_input("Please enter lower value for the number of molecules: "))
        nummax = int(raw_input("Please enter upper value for the number of molecules: "))
        numstep = int(raw_input("Please enter a step: "))
        nr = np.arange(nummin, nummax+1, numstep)
        print("grid: numbers = " +str(nr))
        #!TODO multithreading
        for a in ar:
            for bc in bcr:
                for n in nr:
                    name = pack_micelle(a, bc, float(le), n, pdbfile, int(aa1), int(aa2))
                    #call crysol and find the best solution
                    os.system("rm *.log")
                    os.system("rm *.sav")
                    os.system("rm *.abs")
                    os.system("rm *.alm")
                    os.system("rm *.flm")
                    os.system("crysol " + name + " " + datfile)
                    os.system("primus *.fit")
                    #print("Chi^2 = ")
        os.system("primus *.fit")
        exit()


if len(sys.argv) == 3:
    micfit(sys.argv[1],sys.argv[2])
elif len(sys.argv) == 2 and (sys.argv[1]) == '-h':
    print('''  micfit [<Dat_File>] [<Pdb_file>]
  The first input parameter is a SAXS curve of
  the micelle and the second one is a pdb file of a
  single molecule. The micfit is a python script which
  uses the following external libraries and programs:
  biopython, multiprocessing, packmol, atsas.
  Packmol and atsas must be preinstalled and added
  to the PATH variable.
  Also micfit can be started without arguments in 
  dialog mode.  It automatically assess the geometry
  and number of molecules from the SAXS curve and
  suggest it for the packmol. Different models are 
  built, the best one is proposed as a final
  solution. The quality of model is assessed by
  the CRYSOL fit.
                                                  
  Example:                                       
                                                  
  python micfit.py mic.dat sds.pdb''')
    back = False

while back:
    dat_file = raw_input("Please enter a dat file of micelle ")
    pdb_file = raw_input("Please enter a pdb file name of a single molecule ")
    if os.path.isfile(dat_file) > 0 and os.path.isfile(pdb_file) > 0:
        back = False
        micfit(dat_file, pdb_file)

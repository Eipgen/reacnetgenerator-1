#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
'''
==================
ReacNetGenerator
==================
Automatic generator of reaction network for reactive molecular dynamics simulation.

Plase cite: J. Zeng, L. Cao, J.Z.H. Zhang, C.-H. Chin, T Zhu: ReacNetGen: an Automatic Reaction Network Generator for Reactive Molecular Dynamic Simulations, to be submitted

Author: Jinzhe Zeng, Liqun Cao, John ZH Zhang, Chih-Hao Chin, Tong Zhu
Email: tzhu@lps.ecnu.edu.cn, jzzeng@stu.ecnu.edu.cn

==================
Features
==================
* Processing of MD trajectory containing atomic coordinates or bond orders
* Hidden Markov Model (HMM) based noise filtering
* Isomers identifying accoarding to SMILES
* Generation of reaction network for visualization using force-directed algorithm
* Parallel computing

==================
Simple example
==================
Process a LAMMPS bond file named bonds.reaxc. (See http://lammps.sandia.gov/doc/fix_reax_bonds.html for details)
> from ReacNetGenerator import ReacNetGenerator
> ReacNetGenerator(inputfiletype="lammpsbondfile",inputfilename="bonds.reaxc",atomname=["C","H","O"]).runanddraw()
'''

__version__ = '1.2.15'
__date__ = '2018-03-11'
__update__ = '2018-11-26'
__author__ = 'Jinzhe Zeng'
__email__ = 'jzzeng@stu.ecnu.edu.cn'
__credits__ = ['Jinzhe Zeng', 'Tong Zhu',
               'Liqun Cao', 'Chih-Hao Chin', 'John ZH Zhang']
__copyright__ = 'Copyright 2018, East China Normal University'


import itertools
from functools import reduce
from multiprocessing import Pool, Semaphore, cpu_count
import math
import gc
import time
from collections import Counter
import numpy as np
import networkx as nx
import networkx.algorithms.isomorphism as iso
import matplotlib as mpl
import matplotlib.pyplot as plt
from hmmlearn import hmm
from rdkit.Chem import Draw
from rdkit import Chem
import openbabel
from ase import Atom, Atoms
from ase.io import write as write_xyz
from ReacNetGenerator.reachtml import HTMLResult

plt.switch_backend('Agg')


class ReacNetGenerator(object):
    def __init__(self, inputfiletype="lammpsbondfile", inputfilename="bonds.reaxc", atomname=["C", "H", "O"], selectatoms=None, originfilename=None, hmmfilename=None, atomfilename=None, moleculefilename=None, atomroutefilename=None, reactionfilename=None, tablefilename=None, moleculetempfilename=None, moleculetemp2filename=None, moleculestructurefilename=None, imagefilename=None, speciesfilename=None, resultfilename=None, stepinterval=1, p=[0.5, 0.5], a=[[0.999, 0.001], [0.001, 0.999]], b=[[0.6, 0.4], [0.4, 0.6]], runHMM=True, SMILES=True, getoriginfile=False, species={}, node_size=200, font_size=6, widthcoefficient=1, show=False, maxspecies=20, n_color=256, drawmolecule=False, nolabel=False, needprintspecies=True, filter=[], node_color=[78/256, 196/256, 238/256], pos={}, printfiltersignal=False, showid=True, k=None, start_color=[0, 0, 1], end_color=[1, 0, 0], nproc=None, speciescenter=None):
        def setparam(x, default): return x if x else default
        self.inputfiletype = inputfiletype
        self.inputfilename = inputfilename
        self.atomname = atomname
        self.selectatoms = setparam(selectatoms, self.atomname)

        def setfilename(name, suffix): return setparam(
            name, inputfilename+"."+suffix)
        self.originfilename = setfilename(originfilename, "origin")
        self.hmmfilename = setfilename(hmmfilename, "hmm")
        self.atomfilename = setfilename(atomfilename, "atom")
        self.moleculefilename = setfilename(moleculefilename, "moname")
        self.atomroutefilename = setfilename(atomroutefilename, "route")
        self.reactionfilename = setfilename(reactionfilename, "reaction")
        self.tablefilename = setfilename(tablefilename, "table")
        self.moleculetempfilename = setfilename(moleculetempfilename, "temp")
        self.moleculetemp2filename = setfilename(
            moleculetemp2filename, "temp2")
        self.moleculestructurefilename = setfilename(
            moleculestructurefilename, "structure")
        self.imagefilename = setfilename(imagefilename, "svg")
        self.speciesfilename = setfilename(speciesfilename, "species")
        self.resultfilename = setfilename(resultfilename, "html")
        self.stepinterval = stepinterval
        self.p = np.array(p)
        self.a = np.array(a)
        self.b = np.array(b)
        self.runHMM = runHMM
        self.SMILES = SMILES
        self.getoriginfile = getoriginfile if self.runHMM else True
        self.species = species
        self.needprintspecies = needprintspecies
        self.node_size = node_size
        self.font_size = font_size
        self.widthcoefficient = widthcoefficient
        self.show = show
        self.maxspecies = maxspecies
        self.n_color = n_color
        self.drawmolecule = drawmolecule
        self.nolabel = nolabel
        self.filter = filter
        self.node_color = np.array(node_color)
        self.pos = pos
        self.printfiltersignal = printfiltersignal
        self.showid = showid
        self.k = k
        self.start_color = np.array(start_color)
        self.end_color = np.array(end_color)
        self.nproc = nproc if nproc else cpu_count()
        self.loggingfreq = 1000
        self.speciescenter = speciescenter
        self.timearray = []
        self.statusid = 0
        self.statusidmax = 0

    def runanddraw(self, run=True, draw=True, report=True):
        self.statusidmax = max(
            self.statusidmax, (6 if report else (5 if draw else 4)))
        self.printtime(0)
        if run:
            self.run()
        if draw:
            self.draw()
        if report:
            self.report()

    def run(self):
        self.statusidmax = max(self.statusidmax, 4)
        self.printtime(0)
        for runstep in range(1, 5):
            if(runstep == 1):
                if self.inputfiletype == "lammpsbondfile":
                    readNfunc = self.readlammpsbondN
                    readstepfunc = self.readlammpsbondstep
                elif self.inputfiletype == "lammpscrdfile" or self.inputfiletype == "lammpsdumpfile":
                    readNfunc = self.readlammpscrdN
                    readstepfunc = self.readlammpscrdstep
                self.readinputfile(readNfunc, readstepfunc)
            elif(runstep == 2):
                if self.runHMM:
                    self.initHMM()
                self.calhmm()
            elif(runstep == 3):
                if self.SMILES:
                    self.printmoleculeSMILESname()
                else:
                    self.printmoleculename()
                atomeach = self.getatomeach()
                allmoleculeroute = self.printatomroute(atomeach)
            elif(runstep == 4):
                allroute = self.getallroute(allmoleculeroute)
                self.printtable(allroute)
                if self.needprintspecies:
                    self.printspecies()
            # garbage collect
            gc.collect()
            self.printtime(runstep)

    def draw(self):
        self.statusidmax = max(self.statusidmax, 5)
        self.printtime(0)
        # read table
        table, name = self.readtable()
        species, showname = self.handlespecies(name)

        # make color
        colorsRGB = [(self.start_color+i*(self.end_color-self.start_color) /
                      self.n_color) for i in np.arange(self.n_color)]

        G = nx.DiGraph()
        for i in range(len(table)):
            if name[i] in species and not name[i] in self.filter:
                G.add_node(showname[name[i]] if name[i]
                           in showname else name[i])
                for j in range(len(table)):
                    if name[j] in species and not name[j] in self.filter:
                        if table[i][j] > 0:
                            G.add_weighted_edges_from([((showname[name[i]] if name[i] in showname else name[i]), (
                                showname[name[j]] if name[j] in showname else name[j]), table[i][j])])
        weights = np.array([math.log(G[u][v]['weight']+1)
                            for u, v in G.edges()])
        #widths=[weight/max(weights) *self.widthcoefficient for weight in weights]
        widths = [weight/max(weights) * self.widthcoefficient*2 if weight > max(weights)
                  * 0.7 else weight/max(weights) * self.widthcoefficient*0.5 for weight in weights]
        colors = [colorsRGB[math.floor(
            weight/max(weights)*(self.n_color-1))] for weight in weights]
        try:
            self.pos = (nx.spring_layout(G) if not self.pos else nx.spring_layout(G, pos=self.pos, fixed=[p for p in self.pos])) if not self.k else (
                nx.spring_layout(G, k=self.k) if not self.pos else nx.spring_layout(G, pos=self.pos, fixed=[p for p in self.pos], k=self.k))
            self.logging()
            self.logging("The position of the species in the network is:")
            self.logging(self.pos)
            self.logging()
            for with_labels in ([True] if not self.nolabel else [True, False]):
                nx.draw(G, pos=self.pos, width=widths, node_size=self.node_size, font_size=self.font_size,
                        with_labels=with_labels, edge_color=colors, node_color=self.node_color)
                plt.savefig(
                    self.imagefilename if with_labels else "nolabel_"+self.imagefilename)
                if self.show:
                    plt.show()
                plt.close()
        except Exception as e:
            self.logging("Error: cannot draw images. Details:", e)
        timearray = self.printtime(5)

    def report(self):
        self.statusidmax = max(self.statusidmax, 6)
        self.printtime(0)
        HTMLResult(reactionfile=self.reactionfilename, resultfile=self.resultfilename,
                   imagefile=self.imagefilename, n_thread=self.nproc).report()
        self.printtime(6)

    def logging(self, *message, end='\n'):
        if message:
            localtime = time.asctime(time.localtime(time.time()))
            print(localtime, __name__, __version__, *message, end=end)
        else:
            print(end=end)

    def loggingprocessing(self, index):
        if index % self.loggingfreq == 0:
            self.logging("processing", index, "...", end='\r')

    @property
    def status(self):
        return ["Init", "Read bond information and Detect molecules", "HMM filter", "Indentify isomers and collect reaction paths", "Reaction matrix generation", "Draw reaction network", "Generate analysis report"][self.statusid]

    def printtime(self, statusid):
        self.statusid = statusid
        if len(self.timearray) == 0 or self.statusid > 0:
            self.timearray.append(time.time())
            if statusid > 0:
                self.logging("Step %d: Done! Time consumed: %f s (%s)" % (
                    len(self.timearray)-1, self.timearray[-1]-self.timearray[-2], self.status))
            if statusid >= self.statusidmax:
                self.logging("====== Summary ======")
                self.logging("Total time: %.3f s" %
                             (self.timearray[-1]-self.timearray[0]))

    def union_dict(self, x, y):
        for k, v in y.items():
            if k in x.keys():
                x[k] += v
            else:
                x[k] = v
        return x

    def mo(self, i, bond, level, molecule, done, bondlist):  # connect molecule
        molecule.append(i)
        done[i] = True
        for j in range(len(bond[i])):
            b = bond[i][j]
            l = level[i][j]
            bo = (i, b, l) if i < b else (b, i, l)
            if not bo in bondlist:
                bondlist.append(bo)
            if not done[b]:
                molecule, done, bondlist = self.mo(
                    b, bond, level, molecule, done, bondlist)
        return molecule, done, bondlist

    def readinputfile(self, readNfunc, readstepfunc):
        steplinenum = readNfunc()
        self.getdandtimestep(readstepfunc, steplinenum)

    def readlammpsbondN(self):
        with open(self.inputfilename) as file:
            iscompleted = False
            for index, line in enumerate(file):
                if line.startswith("#"):
                    if line.startswith("# Number of particles"):
                        if iscompleted:
                            stepbindex = index
                            break
                        else:
                            iscompleted = True
                            stepaindex = index
                        N = [int(s) for s in line.split() if s.isdigit()][0]
                        atomtype = np.zeros(N, dtype=np.int)
                else:
                    s = line.split()
                    atomtype[int(s[0])-1] = int(s[1])
        steplinenum = stepbindex-stepaindex
        self.N = N
        self.atomtype = atomtype
        return steplinenum

    def readlammpsbondstep(self, item):
        (step, lines), _ = item
        bond = [[] for x in range(self.N+1)]
        level = [[] for x in range(self.N+1)]
        for line in lines:
            if line:
                if line.startswith("#"):
                    if line.startswith("# Timestep"):
                        timestep = step, [
                            int(s) for s in line.split() if s.isdigit()][0]
                else:
                    s = line.split()
                    for i in range(int(s[2])):
                        bond[int(s[0])].append(int(s[i+3]))
                        bondlevel = round(float(s[i+4+int(s[2])]))
                        if bondlevel == 0:
                            bondlevel = 1
                        level[int(s[0])].append(bondlevel)
        d = self.connectmolecule({}, step, bond, level)
        return d, timestep

    def readlammpscrdN(self):
        with open(self.inputfilename) as f:
            iscompleted = False
            for index, line in enumerate(f):
                if line.startswith("ITEM:"):
                    if line.startswith("ITEM: TIMESTEP"):
                        linecontent = 4
                    elif line.startswith("ITEM: ATOMS"):
                        linecontent = 3
                    elif line.startswith("ITEM: NUMBER OF ATOMS"):
                        linecontent = 1
                    elif line.startswith("ITEM: BOX BOUNDS"):
                        linecontent = 2
                else:
                    if linecontent == 1:
                        if iscompleted:
                            stepbindex = index
                            break
                        else:
                            iscompleted = True
                            stepaindex = index
                        N = int(line.split()[0])
                        atomtype = np.zeros(N, dtype=np.int)
                    elif linecontent == 3:
                        s = line.split()
                        atomtype[int(s[0])-1] = int(s[1])
        steplinenum = stepbindex-stepaindex
        self.N = N
        self.atomtype = atomtype
        return steplinenum

    def readlammpscrdstep(self, item):
        (step, lines), _ = item
        step_atoms = []
        for line in lines:
            if line:
                if line.startswith("ITEM:"):
                    if line.startswith("ITEM: TIMESTEP"):
                        linecontent = 4
                    elif line.startswith("ITEM: ATOMS"):
                        linecontent = 3
                    elif line.startswith("ITEM: NUMBER OF ATOMS"):
                        linecontent = 1
                    elif line.startswith("ITEM: BOX BOUNDS"):
                        linecontent = 2
                else:
                    if linecontent == 3:
                        s = line.split()
                        step_atoms.append(
                            (int(s[0]), Atom(self.atomname[int(s[1])-1], [float(x) for x in s[2:5]])))
                    elif linecontent == 4:
                        timestep = step, int(line.split()[0])
        _, step_atoms = zip(*sorted(step_atoms, key=lambda a: a[0]))
        step_atoms = Atoms(step_atoms)
        bond, level = self.getbondfromcrd(step_atoms, step)
        d = self.connectmolecule({}, step, bond, level)
        return d, timestep

    def getdandtimestep(self, readfunc, steplinenum):
        d = {}
        timestep = {}
        with open(self.inputfilename) as file, Pool(self.nproc, maxtasksperchild=100) as pool:
            semaphore = Semaphore(360)
            results = pool.imap_unordered(readfunc, self.produce(semaphore, enumerate(itertools.islice(
                itertools.zip_longest(*[file]*steplinenum), 0, None, self.stepinterval)), None), 10)
            for index, (dstep, timesteptuple) in enumerate(results):
                self.loggingprocessing(index)
                d = self.union_dict(d, dstep)
                step, thetimestep = timesteptuple
                timestep[step] = thetimestep
                semaphore.release()
        self.writemoleculetempfile(d)
        self.timestep = timestep
        self.step = len(timestep)-1

    def connectmolecule(self, d, step, bond, level):
        # init
        done = np.zeros(self.N+1, dtype=bool)
        # connect molecule
        for i in range(1, self.N+1):
            if not done[i]:
                mole, done, bondlist = self.mo(i, bond, level, [], done, [])
                mole.sort()
                bondlist.sort()
                if (tuple(mole), tuple(bondlist)) in d:
                    d[(tuple(mole), tuple(bondlist))].append(step)
                else:
                    d[(tuple(mole), tuple(bondlist))] = [step]
        return d

    def writemoleculetempfile(self, d):
        with open(self.moleculetempfilename, 'w') as f:
            for item in d.items():
                key, value = item
                print(",".join([str(x) for x in key[0]]), ";".join([",".join(
                    [str(y) for y in x]) for x in key[1]]), ",".join([str(x) for x in value]), file=f)

    def getbondfromcrd(self, step_atoms, step, filename="crd"):
        xyzfilename = filename+"_"+str(step)+".xyz"
        mol2filename = filename+"_"+str(step)+".mol2"
        write_xyz(xyzfilename, step_atoms, format='xyz')
        conv = openbabel.OBConversion()
        conv.OpenInAndOutFiles(xyzfilename, mol2filename)
        conv.Convert()
        conv.CloseOutFile()
        bond, bondlevel = self.getbondfrommol2(len(step_atoms), mol2filename)
        return bond, bondlevel

    def getbondfrommol2(self, atomnumber, mol2filename):
        linecontent = -1
        bond = [[] for i in range(atomnumber+1)]
        bondlevel = [[] for i in range(atomnumber+1)]
        with open(mol2filename) as f:
            for line in f:
                if line.startswith("@<TRIPOS>BOND"):
                    linecontent = 0
                else:
                    if linecontent == 0:
                        s = line.split()
                        bond[int(s[1])].append(int(s[2]))
                        bond[int(s[2])].append(int(s[1]))
                        level = 12 if s[3] == 'ar' else int(s[3])
                        bondlevel[int(s[1])].append(level)
                        bondlevel[int(s[2])].append(level)
        return bond, bondlevel

    def initHMM(self):
        self.model = hmm.MultinomialHMM(n_components=2)
        self.model.startprob_ = self.p
        self.model.transmat_ = self.a
        self.model.emissionprob_ = self.b

    def produce(self, semaphore, plist, parameter):
        for item in plist:
            semaphore.acquire()
            yield item, parameter

    def getoriginandhmm(self, item):
        line, _ = item
        s = line.split()
        value = np.array([int(x)-1 for x in s[-1].split(",")])
        origin = np.zeros(self.step, dtype=np.int)
        origin[value] = 1
        if self.runHMM:
            _, hmm = self.model.decode(
                np.array([origin]).T, algorithm="viterbi")
        return origin, (np.array(hmm) if self.runHMM else np.array([])), line

    def calhmm(self):
        with open(self.originfilename, 'w') if self.getoriginfile or not self.runHMM else Placeholder() as fo, open(self.hmmfilename, 'w') if self.runHMM else Placeholder() as fh, open(self.moleculetempfilename) as ft, open(self.moleculetemp2filename, 'w') as ft2, Pool(self.nproc, maxtasksperchild=100) as pool:
            semaphore = Semaphore(360)
            results = pool.imap_unordered(
                self.getoriginandhmm, self.produce(semaphore, ft, ()), 10)
            for index, (originsignal, hmmsignal, mlist) in enumerate(results):
                self.loggingprocessing(index)
                if 1 in hmmsignal or self.printfiltersignal or not self.runHMM:
                    if self.getoriginfile:
                        print("".join([str(i) for i in originsignal]), file=fo)
                    if self.runHMM:
                        print("".join([str(i) for i in hmmsignal]), file=fh)
                    print(mlist, end='', file=ft2)
                semaphore.release()

    def getatomroute(self, item):
        (i, (atomeachi, atomtypei)), _ = item
        route = []
        routestrarr = []
        moleculeroute = []
        molecule = -1
        right = -1
        for j in range(0, self.step):
            if atomeachi[j] > 0 and atomeachi[j] != molecule:
                routestrarr.append("%s (%d step %d)" % (
                    self.mname[atomeachi[j]-1], atomeachi[j], self.timestep[j]))
                left = right
                molecule = atomeachi[j]
                right = molecule
                if self.atomname[atomtypei-1] in self.selectatoms:
                    if left >= 0 and not (left, right) in moleculeroute:
                        moleculeroute.append((left, right))
        routestr = "Atom %d %s: " % (
            i, self.atomname[atomtypei-1])+" -> ".join(routestrarr)
        return moleculeroute, routestr

    def printatomroute(self, atomeach):
        with open(self.atomroutefilename, 'w') as f, Pool(self.nproc, maxtasksperchild=100) as pool:
            allmoleculeroute = []
            semaphore = Semaphore(360)
            results = pool.imap(self.getatomroute, self.produce(
                semaphore, enumerate(zip(atomeach, self.atomtype), start=1), ()), 10)
            for index, route in enumerate(results):
                self.loggingprocessing(index)
                moleculeroute, routestr = route
                print(routestr, file=f)
                for mroute in moleculeroute:
                    if not mroute in allmoleculeroute:
                        allmoleculeroute.append(mroute)
                semaphore.release()
        return allmoleculeroute

    def makemoleculegraph(self, atoms, bonds):
        G = nx.Graph()
        for line in bonds:
            G.add_edge(line[0], line[1], level=line[2])
        for atom in atoms:
            atomnumber, atomtype = atom
            G.add_node(atomnumber, atom=atomtype)
        return G

    def getstructure(self, name, atoms, bonds):
        index = {}
        for i, atom in enumerate(atoms, start=1):
            index[atom] = i
        return name+" "+",".join([self.atomname[self.atomtype[x-1]-1] for x in atoms])+" "+";".join([str(index[x[0]])+","+str(index[x[1]])+","+str(x[2]) for x in bonds])

    def readstrcture(self):
        with open(self.moleculestructurefilename) as f:
            d = {}
            for line in f:
                s = line.split()
                name = s[0]
                atoms = [x for x in s[1].split(",")]
                bonds = [tuple(int(y) for y in x.split(","))
                         for x in s[2].split(";")] if len(s) == 3 else []
                d[name] = (atoms, bonds)
        return d

    def printmoleculename(self):
        mname = []
        d = {}
        em = iso.numerical_edge_match(['atom', 'level'], ["None", 1])
        with open(self.moleculefilename, 'w') as fm, open(self.moleculetemp2filename) as ft, open(self.moleculestructurefilename, 'w') as fs:
            for line in ft:
                s = line.split()
                atoms = np.array([int(x) for x in s[0].split(",")])
                bonds = np.array([tuple(int(y) for y in x.split(","))
                                  for x in s[1].split(";")] if len(s) == 3 else [])
                typenumber = np.zeros(len(self.atomname), dtype=np.int)
                atomtypes = []
                for atomnumber in atoms:
                    typenumber[self.atomtype[atomnumber-1]-1] += 1
                    atomtypes.append((atomnumber, self.atomtype[atomnumber-1]))
                G = self.makemoleculegraph(atomtypes, bonds)
                name = "".join([self.atomname[i]+(str(typenumber[i] if typenumber[i] > 1 else ""))
                                if typenumber[i] > 0 else "" for i in range(0, len(self.atomname))])
                if name in d:
                    for j in range(len(d[name])):
                        if nx.is_isomorphic(G, d[name][j], em):
                            if j > 0:
                                name += "_"+str(j+1)
                            break
                    else:
                        d[name].append(G)
                        name += "_"+str(len(d[name]))
                        print(self.getstructure(name, atoms, bonds), file=fs)
                else:
                    d[name] = [G]
                    print(self.getstructure(name, atoms, bonds), file=fs)
                mname.append(name)
                print(name, ",".join([str(x) for x in atoms]), ";".join(
                    [",".join([str(y) for y in x]) for x in bonds]), file=fm)
        self.mname = mname

    def calmoleculeSMILESname(self, item):
        line, _ = item
        s = line.split()
        atoms = np.array([int(x) for x in s[0].split(",")])
        bonds = np.array([tuple(int(y) for y in x.split(","))
                          for x in s[1].split(";")] if len(s) == 3 else [])
        type = {}
        for atomnumber in atoms:
            type[atomnumber] = self.atomname[self.atomtype[atomnumber-1]-1]
        name = self.convertSMILES(atoms, bonds, type)
        return name, atoms, bonds

    def printmoleculeSMILESname(self):
        mname = []
        with open(self.moleculefilename, 'w') as fm, open(self.moleculetemp2filename) as ft, Pool(self.nproc, maxtasksperchild=100) as pool:
            semaphore = Semaphore(360)
            results = pool.imap(self.calmoleculeSMILESname,
                                self.produce(semaphore, ft, ()), 10)
            for index, result in enumerate(results):
                self.loggingprocessing(index)
                name, atoms, bonds = result
                mname.append(name)
                print(name, ",".join([str(x) for x in atoms]), ";".join(
                    [",".join([str(y) for y in x]) for x in bonds]), file=fm)
                semaphore.release()
        self.mname = mname

    def convertSMILES(self, atoms, bonds, type):
        m = Chem.RWMol(Chem.MolFromSmiles(''))
        d = {}
        for atomnumber in atoms:
            d[atomnumber] = m.AddAtom(Chem.Atom(type[atomnumber]))
        for bond in bonds:
            atom1, atom2, level = bond
            m.AddBond(d[atom1], d[atom2], Chem.BondType.DOUBLE if level == 2 else (
                Chem.BondType.TRIPLE if level == 3 else (Chem.BondType.AROMATIC if level == 12 else Chem.BondType.SINGLE)))
        name = Chem.MolToSmiles(m)
        return name

    def getatomeach(self):
        atomeach = np.zeros((self.N, self.step), dtype=np.int)
        with open(self.hmmfilename if self.runHMM else self.originfilename) as fh, open(self.moleculetemp2filename) as ft:
            for i, (lineh, linet) in enumerate(zip(fh, ft), start=1):
                s = linet.split()
                key1 = np.array([int(x) for x in s[0].split(",")])
                index = np.array(
                    [j for j in range(len(lineh)) if lineh[j] == "1"])
                if(len(index)) > 0:
                    atomeach[key1[:, None]-1, index] = i
        with open(self.atomfilename, 'w') as f:
            for atom in atomeach:
                print(*atom, file=f)
        return atomeach

    def getallroute(self, allmoleculeroute):
        allroute = Counter()
        for moleculeroute in allmoleculeroute:
            leftname = self.mname[moleculeroute[0]-1]
            rightname = self.mname[moleculeroute[1]-1]
            if leftname == rightname:
                continue
            equation = (leftname, rightname)
            allroute[equation] += 1
        return allroute

    def printtable(self, allroute, n_searchspecies=2, maxsize=100):  # speciescenter
        species = []
        table = np.zeros((maxsize, maxsize), dtype=np.int)
        reactionnumber = np.zeros((2), dtype=np.int)
        sortedreactions = sorted(
            allroute.items(), key=lambda d: d[1], reverse=True)
        # added on Nov 17, 2018
        if self.speciescenter:
            def searchspecies(originspec):
                searchedspecies = []
                for reaction, n_reaction in sortedreactions:
                    ii = 1
                    if originspec == reaction[1-ii]:
                        if not reaction[ii] in species:
                            searchedspecies.append(
                                (reaction[ii], (reaction, n_reaction)))
                    if len(searchedspecies) >= n_searchspecies:
                        break
                return searchedspecies

            newreactions = []
            species = [self.speciescenter]
            newspecies = [self.speciescenter]
            while len(species) < maxsize and newspecies:
                newnewspecies = []
                for newspec in newspecies:
                    searchedspecies = searchspecies(newspec)
                    for searchedspec, searchedreaction in searchedspecies:
                        if len(species) < maxsize:
                            newnewspecies.append(searchedspec)
                            species.append(searchedspec)
                            newreactions.append(searchedreaction)
                newspecies = newnewspecies
            for reac in sortedreactions:
                if not reac in newreactions:
                    newreactions.append(reac)
            sortedreactions = newreactions

        with open(self.reactionfilename, 'w') as f:
            for reaction, n_reaction in sortedreactions:
                print(n_reaction, "->".join(reaction), file=f)
                for i, spec in enumerate(reaction):
                    if spec in species:
                        number = species.index(spec)
                    elif len(species) < 100:
                        species.append(spec)
                        number = species.index(spec)
                    else:
                        number = -1
                    reactionnumber[i] = number
                if all(reactionnumber >= 0):
                    table[reactionnumber[0]][reactionnumber[1]] = n_reaction

        with open(self.tablefilename, 'w') as f:
            print("\t"+"\t".join(species), file=f)
            for i in range(len(species)):
                print(species[i], end='\t', file=f)
                for j in range(len(species)):
                    print(table[i][j], end='\t', file=f)
                print(file=f)

    def readtable(self):
        table = []
        name = []
        with open(self.tablefilename) as file:
            for line in itertools.islice(file, 1, None):
                name.append(line.split()[0])
                table.append([int(s) for s in line.split()[1:]])
        return np.array(table), name

    def convertstructure(self, atoms, bonds):
        types = {}
        atomtypes = []
        for atom in enumerate(atoms, start=1):
            atomtypes.append((i, self.atomname.index(atom)))
        G = self.makemoleculegraph(atomtypes, bonds)
        return G

    def handlespecies(self, name):
        showname = {}
        if self.species == {}:
            species_out = dict([(x, {}) for x in (name if len(
                name) <= self.maxspecies else name[0:self.maxspecies])])
        else:
            species_out = {}
            b = True
            for spec in self.species.items():
                specname, value = spec
                if "structure" in value:
                    atoms, bonds = value["structure"]
                    G1 = convertstructure(atoms, bonds)
                    if b:
                        structures = readstrcture()
                        em = iso.numerical_edge_match(
                            ['atom', 'level'], ["None", 1])
                        b = False
                    i = 1
                    while (specname+"_"+str(i) if i > 1 else specname) in structures:
                        G2 = convertstructure(structures[(
                            specname+"_"+str(i) if i > 1 else specname)][0], structures[(specname+"_"+str(i) if i > 1 else specname)][1])
                        if nx.is_isomorphic(G1, G2, em):
                            if i > 1:
                                specname += "_"+str(i)
                            break
                        i += 1
                species_out[specname] = {}
                if "showname" in value:
                    showname[specname] = value["showname"]
        if self.showid:
            if species_out:
                self.logging()
                self.logging("Species are:")
                for n, (specname, value) in enumerate(species_out.items(), start=1):
                    showname[specname] = str(n)
                    print(n, specname)
        return species_out, showname

    def printspecies(self):
        with open(self.moleculetemp2filename) as f2, open(self.speciesfilename, 'w') as fw:
            d = [Counter() for i in range(len(self.timestep))]
            for name, line2 in zip(self.mname, f2):
                for t in [int(x) for x in line2.split()[-1].split(",")]:
                    d[t][name] += 1
            for t in range(len(self.timestep)):
                print("Timestep", self.timestep[t], ":", end=' ', file=fw)
                for name, num in d[t].items():
                    print(name, num, end=' ', file=fw)
                print(file=fw)

    def __enter__(self): return self

    def __exit__(self, Type, value, traceback): pass


class Placeholder(object):
    def __init__(self): pass

    def __enter__(self): return self

    def __exit__(self, Type, value, traceback): pass


if __name__ == 'ReacNetGenerator':
    print(__doc__)
    print("Version: %s" % __version__, "Creation date: %s" %
          __date__, "Update date: %s" % __update__)

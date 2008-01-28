#!/usr/bin/python
"""

Generates a makefile for use with symplicity; also generates a .do
file for use with modelsim.

call with a path to a sim.files list, which has the full path of all
the needed files

How to handle depencencies? Well, we really don't want to compile all
of the files ourselves. But simuli gets really picky about file
modification dates and serial numbers.



"""

import sys
import os.path
import re

archRE = re.compile("architecture (.+) of", re.IGNORECASE)
packageRE = re.compile("package (.+) is", re.IGNORECASE)


class ParseVHDL(object):
    def __init__(self, filename):
        self.filename = filename


    def getEntity(self):
        """
        Return the first entity defined in the file
        """

        fid = file(self.filename)
        entityre = re.compile("entity (\w+) is", re.IGNORECASE)

        matches = entityre.search(fid.read())
        self.entityname =  matches.groups()[0]
        return self.entityname
    def getArch(self):
        
        fid = file(self.filename)
        entityre = re.compile("architecture (\w+) of %s is" % self.entityname,
                              re.IGNORECASE)

        matches = entityre.search(fid.read())
        self.archname =  matches.groups()[0]
        return self.archname.lower()
    
    
class Sonata: 
    def writeTarget(self, mfile, f, deplist= []):
        if len(f) > 1:
            filename = f[0]
            worklib = f[1]
        else:
            filename = f[0]
            worklib = None

        isPackage = False


        # extract out the architecture type
        fid = file(filename)
        filestr = fid.read()
        m = archRE.search(filestr)
        if m:
            archtype =  m.groups()[0]
        else:
            isPackage = True
            m = packageRE.search(filestr)
            packagename = m.groups()[0]
            archtype = "prim"
            #archtype = packagename

        fname = os.path.basename(filename)
        fpre = fname.split(".")[0].lower()
        mfile.write("\n")
        if worklib == None:
            workdir = "$(WORKDIR)"
        else:
            workdir = "%s.sym" % worklib

        if isPackage:
            target = "%s/%s/%s.var" % (workdir, fpre, archtype.lower())
        else:
            target = "%s/%s/_%s.var" % (workdir, fpre, archtype.lower())

        mfile.write("%s: " % target)
        for i in deplist:
            mfile.write("%s " % i[0])
        mfile.write("%s\n" % filename)
        if worklib:
            mfile.write("\t$(VHDLC) -vital2000 -work %s  %s\n" % (worklib, filename))
        else:
            mfile.write("\t$(VHDLC) -vital2000 %s\n" % (filename))

            deplist.append(f)


        return target

    def genMake(self, hwlist, complist, simlist, toplevel ):
        mfile = file("Makefile", 'w')
        # first, standard header:
        VHDLC = "vhdlp"
        VHDLS = "vhdle"
        WORKDIR = "work.sym"

        if toplevel.strip() == "":
            print "Warning; no toplevel specified in conf file"

        mfile.write("VHDLC=%s\n" % VHDLC)
        mfile.write("VHDLS=%s\n" % VHDLS)
        mfile.write("WORKDIR=%s\n" % WORKDIR)

        mfile.write("all: hw comp sim\n")

        hwtgtstr = "hw: "
        deplist = []
        for f in hwlist:
            hwtgtstr += self.writeTarget(mfile, f, deplist) + ' '
            deplist.append(f)

        mfile.write("\n")
        mfile.write(hwtgtstr + '\n')

        comptgtstr = "comp: "
        for f in complist:
            comptgtstr += self.writeTarget(mfile, f) + ' ' 

        mfile.write("\n")
        mfile.write(comptgtstr + '\n')

        simtgtstr = "sim: "
        for f in simlist:
            simtgtstr += self.writeTarget(mfile, f) + ' ' 

        mfile.write("\n")
        mfile.write(simtgtstr + '\n')

        # top level simulation entities:
        mfile.write("runsim: all\n")
        mfile.write("\t$(VHDLS) %s\n" % toplevel);
        mfile.write("\n")

        mfile.write("\nclean:\n")
        mfile.write("\trm -Rf *.sym")
        mfile.write("\n\n")

        mfile.close()

    def parseFile(self, fname):
        fid = file(filename)
        fl = fid.readlines()
        globallist = [] 
        hwlist = []
        complist = []
        simlist = []
        toplevel = ""
        current = hwlist
        for f in fl:
            f = f.strip()
            if f == "hw:":
                current = hwlist
            elif f == "comp:":
                current = complist
            elif f == "sim:":
                current = simlist
            elif f == "":
                pass
            elif f[0:9] =="toplevel:" :
                toplevel = f[10:]
            else:
                current.append(f.split())

        return (hwlist, complist, simlist, toplevel)

class Modelsim:
    def __init__(self):
        self.workdirs = set()
        self.workdirs.add("work")
        
    def writeTarget(self, mfile, f, deplist= []):
        if len(f) > 1:
            filename = f[0]
            worklib = f[1]
        else:
            filename = f[0]
            worklib = None

        isPackage = False


        # extract out the architecture type
        fid = file(filename)
        filestr = fid.read()
        m = archRE.search(filestr)
        if m:
            archtype =  m.groups()[0]
        else:
            isPackage = True
            m = packageRE.search(filestr)
            packagename = m.groups()[0]
            archtype = "prim"
            #archtype = packagename

        fname = os.path.basename(filename)
        pv = ParseVHDL(filename)

        if isPackage:
            fpre = fname.split(".")[0].lower()
        else:
            fpre = pv.getEntity()
                    
        
        mfile.write("\n")
        if worklib == None:
            workdir = "$(WORKDIR)"
        else:
            self.workdirs.add(worklib)
            workdir = "%s" % worklib

        if isPackage:
            target = "%s/%s/body.dat" % (workdir, fpre)
        else:
            target = "%s/%s/%s.dat" % (workdir, fpre, pv.getArch())

        mfile.write("%s: %s/touched " %  (target, workdir))
        for i in deplist:
            mfile.write("%s " % i[0])
            
        mfile.write("%s\n" % filename)
        if worklib:
            mfile.write("\tmkdir -p %s\n" % workdir) 
            mfile.write("\t$(VHDLC) -work %s  %s\n" % (worklib, filename))
        else:
            mfile.write("\tmkdir -p %s\n" % workdir) 
            mfile.write("\t$(VHDLC) %s\n" % (filename))

            deplist.append(f)


        return target

    def genMake(self, hwlist, complist, simlist, toplevel ):
        mfile = file("Makefile", 'w')
        # first, standard header:
        VHDLC = "vcom"
        VHDLS = "vsim"
        VHDLL = "vlib"
        WORKDIR = "work"

        if toplevel.strip() == "":
            print "Warning; no toplevel specified in conf file"

        mfile.write("VHDLC=%s\n" % VHDLC)
        mfile.write("VHDLS=%s\n" % VHDLS)
        mfile.write("WORKDIR=%s\n" % WORKDIR)

        mfile.write("all: hw comp sim\n")

        hwtgtstr = "hw: "
        deplist = []
        for f in hwlist:
            hwtgtstr += self.writeTarget(mfile, f, deplist) + ' ' 
            deplist.append(f)
            
        mfile.write("\n")
        mfile.write(hwtgtstr + '\n')

        comptgtstr = "comp: "
        for f in complist:
            comptgtstr += self.writeTarget(mfile, f) + ' ' 

        mfile.write("\n")
        mfile.write(comptgtstr + '\n')

        simtgtstr = "sim: "
        for f in simlist:
            simtgtstr += self.writeTarget(mfile, f) + ' ' 

        mfile.write("\n")
        mfile.write(simtgtstr + '\n')

        # top level simulation entities:
        mfile.write("runsim: all\n")
        mfile.write("\t$(VHDLS) %s\n" % toplevel);
        mfile.write("\n")

        mfile.write("\nclean:\n")
        mfile.write("\trm -Rf ")
        for w in self.workdirs:
            mfile.write("%s " % w)
        mfile.write("\n\n")

        # now add the workdirs
        for w in self.workdirs:
            mfile.write("%s/touched:\n" % w)
            mfile.write("\t%s  %s\n" % (VHDLL, w))
            mfile.write("\ttouch  %s/touched\n" % (w,))


        mfile.close()

    def parseFile(self, fname):
        fid = file(filename)
        fl = fid.readlines()
        globallist = [] 
        hwlist = []
        complist = []
        simlist = []
        toplevel = ""
        current = hwlist
        for f in fl:
            f = f.strip()
            if f == "hw:":
                current = hwlist
            elif f == "comp:":
                current = complist
            elif f == "sim:":
                current = simlist
            elif f == "":
                pass
            elif f[0:9] =="toplevel:" :
                toplevel = f[10:]
            else:
                current.append(f.split())

        return (hwlist, complist, simlist, toplevel)

filename = sys.argv[1]
compileset = Modelsim()
(hwlist, complist, simlist, toplevel) = compileset.parseFile(filename)

compileset.genMake(hwlist, complist, simlist, toplevel)

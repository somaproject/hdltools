#!/usr/bin/python
"""
VHDL testbench framework to integrate with modelsim.

-----------------------------------------------------
General Overview
-----------------------------------------------------

Overview of our modelsim design and test framework for unit testing of
vhdl projects. For each project, there will be a "simulations"
directory, which will contain a series of testbenches of each
subsystem (or type).

Obviously, we'll need behavioral versions of some external components
to create proper test jigs; these live in the components
directory. Thus we have an organization such as:

myproject/
     myproject/ -- PCB, etc.
     vhdl/ -- main VHDL
     simulations/ -- simulations dir
           subsysA/ -- subsystem A
              testsubsysA.vhd -- main testbench, component named testSubsysA
              testsubsysA.do -- do file
           subsysZ/ -- subsystem Z
           components/
               component1/component1.vhd -- an emulation of component 1

There can be more than one simname for a component, although ideally each component would instead have a suite of tests. 

Modelsim:

inside, each has a simname.do file that is a do file for modelsim
which contains all the necessary commands.  The existing .do files
should load all necessary components relative to the directiory which
contains the .do file, and should not include a "run" command.

Symphony EDA:
using gnu make, simply need to run "make sim"

All tests continually check data, and when they fail raise an assert
error of severity error, which we detect and record. The simulation
finishes when we detect an error of severity failure, causing the
simulation to pause. We set this as the break value with

set BreakOnAssertion 2

This code is all designed to be run under windows. 

To report an error:

assert foo = bar
   report "My message"
   severity error;

or, to end:

assert false
    report "End of simulation"
    severity failure;
    

Generics:
   To run a simulation with a certain set of generics, pass a dictionary to the test initialization instance with the generic name as the key and the value as the value. Generic names in the hierarchy can be specified like "/top/foo" or just "bar".

"""

import os, sys, re
import unittest

MODELPATH = "vsim"
MODELARGS = " -c"

class Message(object):
    def __init__(self):
        self.text = ""
        # time is always picoseconds
        self.time = ""
        self.source = ""

class Note(Message):
    pass

class Warning(Message):
    pass

class Error(Message):
    pass

class Failure(Message):
    pass


class ModelVhdlSimTestCase(unittest.TestCase):
    def __init__(self, modulename, basedir = ".", generics={}):
        unittest.TestCase.__init__(self)
        self.modulename = modulename
        self.basedir = basedir 
        self.runtext =""
        self.generics = generics
        self.buildresult = 0
        
    def createDoFile(self):
        """
        Automatic generation of the target .do file
        """

        dostr = """
        vsim -t 1ps %stest
        set BreakOnAssertion 3
        disablebp
        onerror quit
        onbreak quit
        run -All 
        quit
        """

        fid = file("test.do", 'w')
        fid.write(dostr % self.modulename )
        fid.close()
        
        
    def setUp(self):
        self.origdir = os.getcwd()

        os.chdir(self.basedir + '/' + self.modulename)

        os.system("make clean > /tmp/clean.log")
        self.buildresult = os.system("make > /tmp/make.log")

        self.createDoFile()
        
        cmdstr = "%s %s -do test.do" % (MODELPATH, MODELARGS)
        print "model cmdstr = ", cmdstr
        self.stdin, self.stdout = os.popen2(cmdstr)


    def tearDown(self):
        self.stdin.close()
        self.stdout.close()
        os.chdir(self.origdir)

        
    def runTest(self):
        """
        Actually run the test; we incidentally rerun the vsim command
        here as well

        """
        print "Running test" 

        runtext =  self.stdout.read()
        messages = self.getMessages(runtext)


        errors = filter(lambda m: isinstance(m, Error), messages)
        self.assert_(len(errors) == 0, "There were errors in the suite")
        self.assert_(self.buildresult == 0, "There was a problem building the suite")
        
    def getMessages(self, string):
        msgre = re.compile("# \*\* (Note|Warning|Error|Failure): (.+)(\n.+)*?\n#    Time: (\d+) (\w+) .+(Process|Instance): ([\w//]+)")


        results = []

        for i in  msgre.findall(string):
            msg = None
            if i[0] == "Warning":
                msg = Warning()
            elif i[0] == "Note" :
                msg = Note()
            elif i[0] == "Error":
                msg = Error()
            elif i[0] == "Failure":
                msg = Failure()

            msg.text = i[1]

            time = long(i[-4])
            if i[-3] == "ps":
                time = time / 1000
            msg.time = time

            msg.source = i[-2] + ':' + i[-1]

            results.append(msg)

        return results

class SymphonyVhdlSimTestCase(unittest.TestCase):
    def __init__(self, modulename, basedir = ".", generics={}):
        unittest.TestCase.__init__(self)
        self.VHDLSIM = "vhdle"

        self.modulename = modulename
        self.basedir = basedir 
        self.generics = generics
        
    def setUp(self):
        pass # no strange set-up here
        
    def tearDown(self):
        os.chdir(self.origdir)

        
    def runTest(self):
        """
        Actually run the test;

        """
        self.origdir = os.getcwd()
        os.chdir(self.basedir + '/' + self.modulename)
        os.system("make clean > /tmp/clean.log")
        cmdstr = "make runsim > /tmp/sim.log 2>&1" # % (self.VHDLSIM, self.modulename)
        os.system(cmdstr)
        
        fid = file("/tmp/sim.log")
        runtext = fid.read()
        
        messages = self.getMessages(runtext)
        errors = filter(lambda m: isinstance(m, Error), messages)
        self.assert_(len(errors) == 0, "There were errors in the suite")

        self.assert_(self.getBuildErrors(runtext) == [], "There were build errors in " + self.modulename)
        
    def getBuildErrors(self, string):
        bre = re.compile("(Error): (.+)")

        errors = []
        for i in bre.findall(string):
            errors.append(i)
        return errors

    def getMessages(self, string):
        msgre = re.compile("(REPORT|ASSERT): (NOTE|WARNING|ERROR|FAILURE) at (.+): (..+)")

        results = []

        for i in  msgre.findall(string):

            msg = None
            cmd = i[1].lower()
            if cmd == "warning":
                msg = Warning()
            elif cmd == "note":
                msg = Note()
            elif cmd == "error":
                msg = Error()
            elif cmd == "failure":
                msg = Failure()
            else:
                print i
                raise "UNKNOWN MESSAGE:|" + str(cmd) + "|"

            if cmd == "note":
                msg.text = i[2]

                msg.time = 0

                results.append(msg)

            elif cmd == "failure":
                msg.text = i[3]

                msg.time = 0

                results.append(msg)

            else:
                msg.text = i[3]

                msg.time = i[2]

                results.append(msg)

            
        return results

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(SymphonyVhdlSimTestCase("fibertx", "."))
    

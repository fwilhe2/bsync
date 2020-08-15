import unittest, tempfile, os, subprocess, shutil, inspect

dir1 = "dir1"
dir2 = "dir2"

from bsync import main as bsync_main
from bsync import args as bsync_args


def unittest_verbosity():
    """Return the verbosity setting of the currently running unittest
       program, or 0 if none is running.
       (https://stackoverflow.com/a/32883243/1259360)
    """
    frame = inspect.currentframe()
    while frame:
        self = frame.f_locals.get('self')
        if isinstance(self, unittest.TestProgram):
            return self.verbosity
        frame = frame.f_back
    return 0


class TestBase(unittest.TestCase):

    def setUp(self):
        self._verbosity = unittest_verbosity()
        # self._tempdir = tempfile.mkdtemp()
        self._tempdir = os.path.join(os.path.abspath(os.path.curdir), 'temp')
        try:
            os.mkdir(self._tempdir)
        except FileExistsError as ex:
            shutil.rmtree(self._tempdir)
            os.mkdir(self._tempdir)
        self.dir1 = os.path.join(self._tempdir, dir1)
        self.dir2 = os.path.join(self._tempdir, dir2)
        os.mkdir(self.dir1)
        os.mkdir(self.dir2)
        self.counter = 0
        print(f'Created directories {self.dir1} , {self.dir2}')

    def tearDown(self):
        # input(f'About to remove contents of {self._tempdir} . Press ENTER')
        shutil.rmtree(self._tempdir)
        pass

    def bsync(self, args):
        verbArg = []
        if self._verbosity >= 2:
            verbArg = ["-v"]
        bsync_args.read_from_commandline(force_arg_list=verbArg + args + [self.dir1, self.dir2])
        print("bsync" + " ".join(args + [self.dir1, self.dir2]))

        return bsync_main(bsync_args)

    def bsync_shell(self, args):
        command = ["bsync"] + args + [self.dir1, self.dir2]
        print(" ".join(command))
        with subprocess.Popen(" ".join(command), shell=True, stdout=subprocess.PIPE) as proc:
            fd = proc.stdout
            output = fd.read()
            fd.close()
            proc.wait()
            self.assertEqual(proc.returncode, 0, "bsync failed with code %d" % proc.returncode)
        return output

    def _val(self, num):
        return "o" * num

    def updfile(self, dir, name):
        """
        update the provided file(s), write counter * o characters, and increase counter
        :param dir:
        :param name:
        """

        for n in name if type(name) is list else [name]:
            with open(os.path.join(self._tempdir, dir, n), "w") as f:
                f.write(self._val(self.counter))
                self.counter += 1

    def delfile(self, dir, name):
        os.remove(os.path.join(self._tempdir, dir, name))

    def assertExists(self, dir, name, msg=None):
        for n in name if type(name) is list else [name]:
            self.assertTrue(os.path.exists(os.path.join(self._tempdir, dir, n)), msg)

    def assertNotExists(self, dir, name, msg=None):
        for n in name if type(name) is list else [name]:
            self.assertFalse(os.path.exists(os.path.join(self._tempdir, dir, n)), msg)

    def assertFileContains(self, dir, name, value, msg=None):
        self.assertExists(dir, name, msg)
        with open(os.path.join(self._tempdir, dir, name), "r") as f:
            rvalue = f.read()
            self.assertEqual(rvalue, self._val(value))


class TestSync(TestBase):

    def test_1_to_2(self):
        self.updfile(dir1, ["a", "b"])
        self.bsync(["-b"])
        self.assertExists(dir2, ["a", "b"])
        self.assertFileContains(dir2, "a", 0)
        self.assertFileContains(dir2, "b", 1)

    def test_2_to_1(self):
        self.updfile(dir2, ["a", "b"])
        self.bsync(["-b"])
        self.assertExists(dir1, ["a", "b"])
        self.assertFileContains(dir1, "a", 0)
        self.assertFileContains(dir1, "b", 1)

    def test_upd(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "b")
        self.bsync(["-b"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 2)
        self.assertFileContains(dir1, "b", 3)
        self.assertFileContains(dir2, "b", 3)

    def test_del(self):
        self.test_1_to_2()
        self.delfile(dir1, "a")
        self.delfile(dir2, "b")
        self.bsync(["-b"])
        self.assertNotExists(dir1, ["a", "b"])
        self.assertNotExists(dir2, ["a", "b"])

    def test_conflict(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "a")
        self.updfile(dir1, "b")
        self.delfile(dir2, "b")
        self.updfile(dir1, "c")
        self.bsync(["-b"])
        self.bsync(["-b"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 3)
        self.assertFileContains(dir1, "b", 4)
        self.assertNotExists(dir2, "b")


class TestMirror(TestBase):

    def test_1_to_2(self):
        self.updfile(dir1, ["a", "b"])
        self.bsync(["-bm", "mirror"])
        self.assertExists(dir2, ["a", "b"])
        self.assertFileContains(dir2, "a", 0)
        self.assertFileContains(dir2, "b", 1)

    def test_2_to_1(self):
        self.updfile(dir2, ["a", "b"])
        self.bsync(["-bm", "mirror"])
        self.assertNotExists(dir1, ["a", "b"])
        self.assertExists(dir2, ["a", "b"])

    def test_upd(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "b")
        self.bsync(["-bm", "mirror"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 2)
        self.assertFileContains(dir1, "b", 1)
        self.assertFileContains(dir2, "b", 3)

    def test_del(self):
        self.test_1_to_2()
        self.delfile(dir1, "a")
        self.delfile(dir2, "b")
        self.bsync(["-bm", "mirror"])
        self.assertNotExists(dir1, "a")
        self.assertFileContains(dir1, "b", 1)
        self.assertNotExists(dir2, ["a", "b"])

    def test_conflict(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "a")
        self.updfile(dir1, "b")
        self.delfile(dir2, "b")
        self.updfile(dir1, "c")
        self.bsync(["-bm", "mirror"])
        self.bsync(["-bm", "mirror"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 3)
        self.assertFileContains(dir1, "b", 4)
        self.assertNotExists(dir2, "b")


class TestBackup(TestBase):

    def test_1_to_2(self):
        self.updfile(dir1, ["a", "b"])
        self.bsync(["-bm", "backup"])
        self.assertExists(dir2, ["a", "b"])
        self.assertFileContains(dir2, "a", 0)
        self.assertFileContains(dir2, "b", 1)

    def test_2_to_1(self):
        self.updfile(dir2, ["a", "b"])
        self.bsync(["-bm", "backup"])
        self.assertNotExists(dir1, ["a", "b"])
        self.assertExists(dir2, ["a", "b"])

    def test_upd(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "b")
        self.bsync(["-bm", "backup"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 2)
        self.assertFileContains(dir1, "b", 1)
        self.assertFileContains(dir2, "b", 3)

    def test_del(self):
        self.test_1_to_2()
        self.delfile(dir1, "a")
        self.delfile(dir2, "b")
        self.bsync(["-bm", "backup"])
        self.assertNotExists(dir1, "a")
        self.assertFileContains(dir2, "a", 0)
        self.assertFileContains(dir1, "b", 1)
        self.assertNotExists(dir2, "b")

    def test_conflict(self):
        self.test_1_to_2()
        self.updfile(dir1, "a")
        self.updfile(dir2, "a")
        self.updfile(dir1, "b")
        self.delfile(dir2, "b")
        self.updfile(dir1, "c")
        self.bsync(["-bm", "backup"])
        self.bsync(["-bm", "backup"])
        self.assertFileContains(dir1, "a", 2)
        self.assertFileContains(dir2, "a", 3)
        self.assertFileContains(dir1, "b", 4)
        self.assertNotExists(dir2, "b")


class TestMixed(TestBase):

    def _1_to_2(self):
        self.updfile(dir1, ["a", "b"])
        self.bsync(["-b"])
        self.assertExists(dir2, ["a", "b"])
        self.assertFileContains(dir2, "a", 0)
        self.assertFileContains(dir2, "b", 1)

    def test_sync_after_backup(self):
        self._1_to_2()
        self.delfile(dir1, "a")
        self.updfile(dir2, "b")
        self.updfile(dir1, "c")
        self.bsync(["-bm", "backup"])
        self.bsync(["-b"])
        self.assertNotExists(dir1, "a")
        self.assertNotExists(dir2, "a")
        self.assertFileContains(dir1, "b", 2)
        self.assertFileContains(dir2, "b", 2)

    def test_mirror_after_backup(self):
        self._1_to_2()
        self.delfile(dir1, "a")
        self.updfile(dir2, "b")
        self.updfile(dir1, "c")
        self.bsync(["-bm", "backup"])
        self.bsync(["-bm", "mirror"])
        self.assertNotExists(dir1, "a")
        self.assertNotExists(dir2, "a")
        self.assertFileContains(dir1, "b", 1)
        self.assertFileContains(dir2, "b", 2)


if __name__ == '__main__':
    unittest.main(verbosity=1)

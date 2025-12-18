from inland_consequences.coastal import _pfracoastal_lib

def test_DecideDDF_Task4():
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    tempStories = 2
    tempFound = 9
    tempBase = 0
    tempWave = 3.1

    ret = lib.DecideDDF_Task4(tempStories, tempFound, tempBase, tempWave)
    assert ret == "2903"
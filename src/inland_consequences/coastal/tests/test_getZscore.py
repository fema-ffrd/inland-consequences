from inland_consequences.coastal import _pfracoastal_lib

def test_getZscore():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_x = 150.0
    test_mean = 100.0
    test_sd = 10.0
    
    ret = lib.getZscore(x=test_x, mean_data = test_mean, sd_data=test_sd)
    
    assert ret == 5.0
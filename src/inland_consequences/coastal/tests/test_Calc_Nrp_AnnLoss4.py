from inland_consequences.coastal import _pfracoastal_lib
import pandas as pd

def test_Calc_Nrp_AnnLoss4():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    test_loss_vals = pd.Series([0,0,79142,285939,436903])
    test_rp_vals = pd.Series([10, 25, 50, 100, 500])
    ret = lib.Calc_Nrp_AnnLoss4(test_loss_vals, test_rp_vals)
    assert ret == 6381.999
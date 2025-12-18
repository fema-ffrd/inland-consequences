import numpy as np
from inland_consequences.coastal import _pfracoastal_lib

def test_get_NNx():
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    test_a_coord = np.array([[1.0,1.0]], np.float32)
    test_b_coords = np.array([[7.0,5.0], [2.0,1.0], [3.0,3.0], [0.0,0.0]], np.float32)
    test_x = 3

    ret = lib.get_NNx(test_b_coords, test_a_coord, test_x)
    assert list(ret.iloc[0:test_x+1, 1]) == [2,4,3]
import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
from pathlib import Path
from scipy.stats import norm
import os
from time import monotonic
from ._pfracoastal_lib import _PFRACoastal_Lib

logger = logging.getLogger("pfraCoastal")

class Inputs:
    BLDG_ATTR_MAP_DATA = {
        "ORIG":["BID", "location", "BLDG_DED", "BLDG_LIMIT", "BLDG_VALUE", "CNT_DED", "CNT_LIMIT", "CNT_VALUE", "NUM_STORIE", "foundation", "BasementFi", "FIRST_FLOO", "DEMft"],
        "IN":["BID", "location", "BLDG_DED", "BLDG_LIMIT", "BLDG_VALUE", "CNT_DED", "CNT_LIM", "CNT_VALUE", "NUM_STORIE", "foundation", "BasementFi", "FIRST_FLOO", "DEMft"],
        "OUT":["BID", "ORIG_ID", "BLDG_DED", "BLDG_LIM", "BLDG_VAL", "CNT_DED", "CNT_LIM", "CNT_VALUE", "STORY", "FOUND", "BASEFIN", "FFH", "DEMFT"],
        "DESC":["new building id", "source building id", "building deductible", "building limit", "building value", "content deductible", "content limit", "content value", "number of stories", "foundation type", "basement finish type", "first floor height", "ground elevation"],
        "DEF":["-1", "-1", "2000", "200000", "200000", "1000", "100000", "100000", "1", "8", "0", "1", "-9999"],
        "TYPE":['int32', 'object', 'int32', 'int32', 'int32', 'int32', 'int32', 'int32', 'int32', 'int32', 'int32', 'int32', 'float64'],
        "CHECK":[0,0,1,1,1,1,1,1,1,1,1,1,1],
        "HDDF":[0,0,0,0,0,0,0,0,1,1,0,1,0],
        "TDDF":[0,0,0,0,0,0,0,0,1,1,1,0,0],
        "ANLYS":[1,0,1,1,1,1,1,1,1,1,1,1,1],
        "DOM":[np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, "[1,2,3]", "[2,4,6,7,8,9]", "[0,1,2]", np.nan, np.nan]
    }
    
    GUTS_ATTR_MAP_DATA = {
        "OUT":["BID", "BFD", "DEM", "FFE", "FFEe", "TWL", "TWLe", "BFDe", "RP", "PVAL", "SWEL", "SWELe", "WET", "Hc", "Hce", "PWL1", "PW13", "PWG3", "DDFfam", "ddf2", "ddf3", "ddf4", "DAMLw", "DAMPr", "DAMUp", "BVAL", "rLOSSLw", "rLOSSBE", "rLOSSUp", "Loss_Lw", "Loss_BE", "Loss_Up"],
        "MIN":[1 for i in range(13)] + [0 for i in range(19)],
        "DESC":["building id", "bldg flood depth", "dem elev", "first floor elev", "FFE error", "total water elev", "TWL error", "BFD error", "retrun period", "probability", "stillwater elev", "SWEL error", "ground wet?", "conditonal wave height", "Hc error", "probability wave < 1ft", "probability wave 1-3ft", "probability wave >= 3ft", "cpfra ddf family", "damage for df2", "damage for df3", "damage for df4", "combined min damage", "combined med damage", "combined max damage", "building value", "raw min loss", "raw best estimate loss", "raw max loss", "adjusted min loss", "adjusted best estimate loss", "adjusted max loss"]
    }
    
    def __init__(self, blabber=True, use_heatmap=True, hm_bandwidth=1100, hm_resolution=500, hm_name="heatmap",
        mc_n=2000, nbounds=tuple([0.0001, 1]), storm_csv='', bldg_path='', bldg_lay=None,
        swel_mpath='', swel_path='', swelA_path='', swelB_path='', waveA_path='', waveB_path='', use_uncertainty=True,
        use_cutoff=True, use_cutoff10=False, use_eWet=True, use_waves=True, use_twl=False, use_wavecut50=False, use_erosion=False,
        use_insurance=False, use_contents=False, use_netcdf=False, use_outcsv=False, bddf_lut_path='',
        bldg_ddf_lut=None, cddf_lut_path=None, cont_ddf_lut=None, proj_prefix='', out_shp_path='',
        GCB_fid="location", GCB_Bded="BLDG_DED", GCB_Blim="BLDG_LIMIT", GCB_Bval="BLDG_VALUE", GCB_Cded="CNT_DED", 
        GCB_Clim="CNT_LIM", GCB_Cval="CNT_VALUE", GCB_Bsto="NUM_STORIE", GCB_Bfou="foundation", GCB_Bbfi="BasementFi", GCB_Bffh="FIRST_FLOO", GCB_Bdem="DEMft") -> object:
        
        self.blabber = blabber
        self.use_heatmap = use_heatmap
        self.hm_bandwidth = hm_bandwidth
        self.hm_resolution = hm_resolution
        self.hm_name = hm_name
        self.mc_n = mc_n
        self.nbounds = nbounds
        
        self.storm_csv = storm_csv
        
        self.bldg_path = bldg_path
        self.bldg_lay = bldg_lay
        
        self.swel_mpath = swel_mpath
        self.swel_path = swel_path
        self.swelA_path = swelA_path
        self.swelB_path = swelB_path
        self.waveA_path = waveA_path
        self.waveB_path = waveB_path
        
        self.use_uncertainty = use_uncertainty
        self.use_cutoff = use_cutoff
        self.use_cutoff10 = use_cutoff10
        self.use_eWet = use_eWet
        self.use_waves = use_waves
        self.use_twl = use_twl
        self.use_wavecut50 = use_wavecut50
        self.use_erosion = use_erosion
        self.use_insurance = use_insurance
        self.use_contents = use_contents
        self.use_netcdf = use_netcdf
        self.use_outcsv = use_outcsv
        
        self.bddf_lut_path = bddf_lut_path
        self.bldg_ddf_lut = bldg_ddf_lut
        
        self.cddf_lut_path = cddf_lut_path
        self.cont_ddf_lut = cont_ddf_lut
        
        self.out_shp_path = out_shp_path
        self.proj_prefix = proj_prefix
        
        self.bldg_attr_map = pd.DataFrame.from_dict(self.BLDG_ATTR_MAP_DATA)
        self.bldg_attr_map.index = list(range(self.bldg_attr_map.shape[0])) # to make sure the row index has labels
        
        self.guts_attr_map = pd.DataFrame.from_dict(self.GUTS_ATTR_MAP_DATA)
        
        self.GCB_fid = GCB_fid
        self.GCB_Bded = GCB_Bded
        self.GCB_Blim = GCB_Blim
        self.GCB_Bval = GCB_Bval
        self.GCB_Cded = GCB_Cded
        self.GCB_Clim = GCB_Clim
        self.GCB_Cval = GCB_Cval
        self.GCB_Bsto = GCB_Bsto
        self.GCB_Bfou = GCB_Bfou
        self.GCB_Bbfi = GCB_Bbfi
        self.GCB_Bffh = GCB_Bffh
        self.GCB_Bdem = GCB_Bdem
    
    @property
    def blabber(self) -> bool:
        return self._blabber
    
    @blabber.setter
    def blabber(self, val: bool) -> None:
        self._blabber = val
    
    @property
    def use_stormsuite(self) -> bool:
        if self.storm_csv not in ('', None) and '.csv' in self.storm_csv and os.path.exists(self.storm_csv):
            return True
        else:
            return False
    
    @property
    def bddf_lut_path(self) -> str:
        return self._bddf_lut_path
    
    @bddf_lut_path.setter
    def bddf_lut_path(self, val: str) -> None:
        self._bddf_lut_path = val
        if '.csv' in val and os.path.exists(val):
            self.bldg_ddf_lut = pd.read_csv(val)
    
    @property
    def blabfile(self) -> str:
        if self.out_shp_path not in (None, '') and os.path.exists(self.out_shp_path) and self.proj_prefix not in (None, ''):
            return os.path.join(self.out_shp_path, self.proj_prefix+"_run.log")
        else:
            return ''
    
    @property
    def GCB_fid(self) -> str:
        return self._GCB_fid
    
    @GCB_fid.setter
    def GCB_fid(self, val: str) -> None:
        self._GCB_fid = val
        self.bldg_attr_map.loc[1,"IN"] = val
    
    @property
    def GCB_Bded(self) -> str:
        return self._GCB_Bded
    
    @GCB_Bded.setter
    def GCB_Bded(self, val: str):
        self._GCB_Bded = val
        self.bldg_attr_map.loc[2,"IN"] = val
    
    @property
    def GCB_Blim(self) -> str:
        return self._GCB_Blim
    
    @GCB_Blim.setter
    def GCB_Blim(self, val: str) -> None:
        self._GCB_Blim = val
        self.bldg_attr_map.loc[3,"IN"] = val
    
    @property
    def GCB_Bval(self) -> str:
        return self._GCB_Bval
    
    @GCB_Bval.setter
    def GCB_Bval(self, val: str) -> None:
        self._GCB_Bval = val
        self.bldg_attr_map.loc[4,"IN"] = val
    
    @property
    def GCB_Cded(self) -> str:
        return self._GCB_Cded
    
    @GCB_Cded.setter
    def GCB_Cded(self, val: str) -> None:
        self._GCB_Cded = val
        self.bldg_attr_map.loc[5,"IN"] = val
    
    @property
    def GCB_Clim(self) -> str:
        return self._GCB_Clim
    
    @GCB_Clim.setter
    def GCB_Clim(self, val: str) -> None:
        self._GCB_Clim = val
        self.bldg_attr_map.loc[6,"IN"] = val
    
    @property
    def GCB_Cval(self) -> str:
        return self._GCB_Cval
    
    @GCB_Cval.setter
    def GCB_Cval(self, val: str) -> None:
        self._GCB_Cval = val
        self.bldg_attr_map.loc[7,"IN"] = val
    
    @property
    def GCB_Bsto(self) -> str:
        return self._GCB_Bsto
    
    @GCB_Bsto.setter
    def GCB_Bsto(self, val: str) -> None:
        self._GCB_Bsto = val
        self.bldg_attr_map.loc[8,"IN"] = val
    
    @property
    def GCB_Bfou(self) -> str:
        return self._GCB_Bfou
    
    @GCB_Bfou.setter
    def GCB_Bfou(self, val: str) -> None:
        self._GCB_Bfou = val
        self.bldg_attr_map.loc[9,"IN"] = val
    
    @property
    def GCB_Bbfi(self) -> str:
        return self._GCB_Bbfi
    
    @GCB_Bbfi.setter
    def GCB_Bbfi(self, val: str) -> None:
        self._GCB_Bbfi = val
        self.bldg_attr_map.loc[10,"IN"] = val
    
    @property
    def GCB_Bffh(self) -> str:
        return self._GCB_Bffh
    
    @GCB_Bffh.setter
    def GCB_Bffh(self, val: str) -> None:
        self._GCB_Bffh = val
        self.bldg_attr_map.loc[11,"IN"] = val
    
    @property
    def GCB_Bdem(self) -> str:
        return self._GCB_Bdem
    
    @GCB_Bdem.setter
    def GCB_Bdem(self, val: str) -> None:
        self._GCB_Bdem = val
        self.bldg_attr_map.loc[12,"IN"] = val


class PFRACoastal:
    def __init__(self) -> object:
        pass
    
    def runPFRACoastal(self, inputs: Inputs) -> None:
        lib = _PFRACoastal_Lib()
        
        # configure logging
        logger.setLevel("INFO")
        if inputs.blabpath:
            fh = logging.FileHandler(inputs.blabpath, mode='a')
            fh.setLevel("INFO")
        else:
            fh = logging.NullHandler()
        
        if inputs.blabber:
            ch = logging.StreamHandler()
            ch.setLevel("INFO")
        else:
            ch = logging.NullHandler()
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    	##############
        #  	STEP 0 - initiate parallel processing
        fullAnalysis_start = monotonic()
        
        lib.write_log("")
        lib.write_log("**********")
        lib.write_log("BEGIN STEP 0. Setup...")
        lib.write_log("")
        lib.write_log("Summary of inputs:")
        
        lib.write_log(f"Buildings: {inputs.bldg_path}")
        lib.write_log("Input Building Attributes...")
        lib.write_log(inputs.bldg_attr_map.iloc[1:12, inputs.bldg_attr_map.columns.get_indexer(["DESC", "IN"])])
        lib.write_log(f"SWEL A: {inputs.swelA_path}")
        lib.write_log(f"SWEL B: {inputs.swelB_path}")
        lib.write_log(f"Use Waves: {inputs.use_waves}")
        if inputs.use_waves:
            lib.write_log(f"WAVES A: {inputs.waveA_path}")
            lib.write_log(f"WAVES B: {inputs.waveB_path}")
        lib.write_log(f"Project Prefix: {inputs.proj_prefix}")
        lib.write_log(f"OUTPUT directory: {inputs.out_shp_path}")
        lib.write_log(f"Use Uncertainty: {inputs.use_uncertainty}")
        lib.write_log(f"Write internal tables: {inputs.use_outcsv}")
        lib.write_log(f"Use Insurance: {inputs.use_insurance}")
        lib.write_log(f"Use Contents: {inputs.use_contents}")
        if inputs.use_contents:
            lib.write_log(f"Contents DDF lut: {inputs.cddf_lut_path}")
        lib.write_log(f"Building DDF lut: {inputs.bddf_lut_path}")
        
        lib.write_log("")
        lib.write_log("Running Average Annualized Losses...")
        lib.write_log("END STEP 0.")
        
        
        ##############
        #  	STEP 1 - Get building points
        #	Load shapefile, drop unrequired fields, rename required fields fields, validate data, export to shapefile
        # 	RESULTS:
        # 	BUILDING.SPDF = Spatial Points Data Frame _BUILDINGS.shp
        # Start timer for step 1
        step1_start = monotonic()
        lib.write_log(' ')
        lib.write_log(' BEGIN STEP 1. Building Data...')
        BUILDING_SPDF = lib.formatBuildings(inputs.bldg_path)
        lib.write_log('Bulding Sample:')
        lib.write_log(str(BUILDING_SPDF.head()))
        
        # write resulting shapefile
        out_shp_lay = fr'{inputs.proj_prefix}_BUILDINGS'
        out_shp_dsn = os.path.join(inputs.out_shp_path, fr'{out_shp_lay}.shp')
        lib.write_log(fr'Writing Buildingds to: {out_shp_dsn}')
        BUILDING_SPDF.to_file(fr'{out_shp_dsn}\{out_shp_lay}.shp')
        
        lib.write_log('END STEP 1.')
        # Calculate seconds elapsed for step 1
        step1_elapsed = math.ceil(monotonic() - step1_start)
        lib.write_log(f'Full Analysis: {step1_elapsed} sec elapsed')
        ##############
        
        ##############
		#  	STEP 2a - Get surge points
		#	load the surge points
		#		if uncertainty, also load SWEL_cl84, make PSURGERR
		# 	RESULTS:
		# 		PSURGE.SPDF
		# 		PSURGE84.SPDF, optional
		# 		PSURGERR.SPDF, optional
  
        step2a_start = monotonic()
        lib.write_log(' ')
        lib.write_log('BEGIN STEP 2a. Import Surge Data...')
        
        # create extensible swel attribute map
        lib.write_log('.creating SWEL attribute map.')
        #open the dbf
        temptab = gpd.read_file(inputs.swelA_path)
        #get all names that begin with 'e'
        tempcols = [col for col in temptab.columns if col.startswith('e')]
        #get the numeric portion of those columns
        rp_avail = [lib.removeNonNumeric(col) for col in tempcols]
        
        # add these to the attribute map
        surge_attr_in = ['SID'] + list(temptab.columns[tempcols])
        SWEL_attr_out = ['SID'] + [f's{x}' for x in rp_avail]
        surge_attr_desc = ['node ID'] + ['surge elevation' for _ in range(len(SWEL_attr_out)-1)]
        surge_attr_default = -99999 
        surge_attr_check = [0] + [1 for _ in range(len(SWEL_attr_out)-1)]
        surge_attr_type = ['numeric' for _ in range(len(SWEL_attr_out))]
        surge_attr_ddc = [0] + [1 for _ in range(len(SWEL_attr_out)-1)]
        SWEL_attr_map = pd.DataFrame({'IN':surge_attr_in,'OUT':SWEL_attr_out,'DESC':surge_attr_desc,'TYPE':surge_attr_type,'DEF':surge_attr_default,'CHECK':surge_attr_check,'DDC':surge_attr_ddc})
        
        # load SWEL BE
        lib.write_log('Surge A (Best Estimate)')
        PSURGE_SPDF = lib.formatSurge(inputs.swelA_path, SWEL_attr_map)
        lib.write_log('Sample Surge A:')
        lib.write_log(str(PSURGE_SPDF.head()))
        
        # if uncertainty, load swel cl84 and create surge SD
        if inputs.use_uncertainty:
            # load SWEL B
            lib.write_log('Surge B (84CL Estimate)')
            PSURGE84_SPDF = lib.formatSurge(inputs.swelB_path, SWEL_attr_map)
            lib.write_log('Sample Surge B:')
            lib.write_log(str(PSURGE84_SPDF.head()))
            
            # subtract A from B to get SD
            SWERR_attr_map = SWEL_attr_map.copy()
            sel = SWEL_attr_map.loc[SWEL_attr_map['DESC'] == 'surge elevation']
            SWERR_attr_map.loc[sel, 'OUT'] = SWERR_attr_map.loc[sel, 'OUT'].str.replace('s','sx', regex=False)
            SWERR_attr_map.loc[sel, 'DESC'] = 'surge error'
            
            PSURGERR_SPDF = PSURGE84_SPDF.copy()
            PSURGERR_SPDF.drop(columns='geometry').columns = SWERR_attr_map["OUT"].tolist()
            
            minus_tab = PSURGERR_SPDF.columns.difference(['geometry'])
            tempcols = [col for col in PSURGERR_SPDF.columns if col.startswith('sx')]
            
            # create a copy of PSURGE and PSURGE84 that converts -999 to NA for calculating 
			# differences
			# Erase copies with the trash collection
            PSURGE_copy_SPDF = PSURGE_SPDF.copy()
            PSURGE_copy_SPDF_mask = PSURGE_copy_SPDF.columns.difference(['geometry'])
            PSURGE_copy_SPDF[PSURGE_copy_SPDF_mask] = PSURGE_copy_SPDF[PSURGE_copy_SPDF_mask].mask(PSURGE_copy_SPDF[PSURGE_copy_SPDF_mask] < -999, np.nan)
            
            PSURGE84_copy_SPDF = PSURGE84_SPDF.copy()
            PSURGE84_copy_SPDF_mask = PSURGE84_copy_SPDF.columns.difference(['geometry'])
            PSURGE84_copy_SPDF[PSURGE84_copy_SPDF_mask] = PSURGE84_copy_SPDF[PSURGE84_copy_SPDF_mask].mask(PSURGE84_copy_SPDF[PSURGE84_copy_SPDF_mask] < -999, np.nan)
            
            for i in tempcols:
                minus_tab[i] = PSURGE84_copy_SPDF[i] - PSURGE_copy_SPDF[i]
                                
            minus_tab_num_cols = minus_tab.select_dtypes(include='number').columns
            minus_tab[minus_tab_num_cols] = minus_tab[minus_tab_num_cols].clip(lower=0)
            
            PSURGERR_SPDF_mask = PSURGERR_SPDF.columns.difference(['geometry'])
            PSURGERR_SPDF[PSURGERR_SPDF_mask] = minus_tab
            
            
            fill_value = float(SWERR_attr_map['DEF'].iloc[-1])
            num_cols = PSURGERR_SPDF.select_dtypes(include='number').columns
            PSURGERR_SPDF[num_cols] = PSURGERR_SPDF[num_cols].fillna(fill_value)
            lib.write_log('Sample Surge Error (B-A):')
            lib.write_log(str(PSURGERR_SPDF.columns.difference('geometry').head()))
            
        # Find the fully NULL nodes in PSURGE .
        # remove those features from each feature class
        PSURGE_SPDF_mask = PSURGE_SPDF.columns.difference('geometry')
        PSURGE_SPDF_filtered = PSURGE_SPDF[PSURGE_SPDF_mask]
        badrows = PSURGE_SPDF_filtered[len(SWEL_attr_map)-1].eq(SWEL_attr_map.iloc[len(SWEL_attr_map)]['DEF'])
        
        if (~badrows).sum() > 0:
            PSURGE_SPDF = PSURGE_SPDF[~badrows]
            PSURGE84_SPDF = PSURGE84_SPDF[~badrows]
            PSURGERR_SPDF = PSURGERR_SPDF[~badrows]
        
        lib.write_log('END STEP 2a.')
        step2a_elapsed = math.ceil(monotonic() - step2a_start)
        lib.write_log(f'Full Analysis: {step2a_elapsed} sec elapsed')

		##############
		#  	STEP 2b - Get waves
		#	load the wave points
		#		if uncertainty, load WAVE_cl84, make WAVE_SD
		# 	RESULTS:
		# 		PWAVE.SPDF, future optional
		# 		PWAVE84.SPDF, optional
		# 		PWAVERR.SPDF, optional
        step2b_start = monotonic()
        lib.write_log(' ')
        lib.write_log('BEGIN STEP 2b. Import Wave Data...')
        
        if inputs.use_waves:
            # Create extensible wave attribute map
            lib.write_log('.creating WAV attribute map.')
            WV_attr_map = SWEL_attr_map.copy()
            sel = WV_attr_map['CHECK'] == 1
            WV_attr_map.loc[sel, 'OUT'] = WV_attr_map.loc[sel, 'OUT'].str.replace('s','w', regex=False)
            WV_attr_map.loc['surge' in WV_attr_map['DESC']]
            WV_attr_map['DESC'] = WV_attr_map['DESC'].str.replace('surge','wave')
            WV_attr_map['DESC'] = WV_attr_map['DESC'].str.replace('elevation','height')
            sel = WV_attr_map['CHECK'] == 1
            WV_attr_map.loc[sel,'DEF'] = -99999
            
            # load Wave BE
            lib.write_log('Wave A (Best Estimate)')
            PWAVE_SPDF = lib.formatSurge(inputs.waveA_path, WV_attr_map)
            lib.write_log('Sample Wave A:')
            lib.write_log(str(PWAVE_SPDF.head()))
            
            # if uncertainty, load waves cl84 and create surge SD
            if inputs.use_uncertainty:
                # load SWEL B
                lib.write_log('Wave B (84CL Estimate)')
                PWAVE84_SPDF = lib.formatSurge(inputs.waveB_path, WV_attr_map)
                lib.write_log('Sample Wave B:')
                lib.write_log(str(PWAVE84_SPDF.head()))
                
                # subtract A from B to get SD
                WVERR_attr_map = WV_attr_map.copy()
                sel = WV_attr_map['DESC'] == 'wave height'
                WVERR_attr_map.loc[sel,'OUT'] = WV_attr_map['OUT'].str.replace('w','wx')
                WVERR_attr_map.loc[sel,'DESC'] = 'wave error'
                
                PWAVERR_SPDF = PWAVE84_SPDF.copy()
                current_cols = [c for c in PWAVERR_SPDF.columns if c != 'geometry']
                new_cols = WVERR_attr_map['OUT'].tolist()
                new_cols = {old: new for old, new in zip(current_cols, new_cols)}
                PWAVERR_SPDF.rename(columns=new_cols)
                
                minus_tab = PWAVERR_SPDF.columns.difference('geometry')
                tempcols = [i for i, col in enumerate(PWAVERR_SPDF.columns) if col.startswith("w")]

				# create a copy of PSURGE and PSURGE84 that converts -99999 to NA for calculating 
				# differences
				# Erase copies with the trash collection
                PWAVE_copy_SPDF = PWAVE_SPDF.copy()
                PWAVE_copy_SPDF_mask = PWAVE_copy_SPDF.columns.difference(['geometry'])
                PWAVE_copy_SPDF[PWAVE_copy_SPDF_mask] = PWAVE_copy_SPDF[PWAVE_copy_SPDF_mask].mask(PWAVE_copy_SPDF[PWAVE_copy_SPDF_mask] < -999, np.nan)
                
                
                PWAVE84_copy_SPDF = PWAVE84_SPDF.copy()
                PWAVE84_copy_SPDF_mask = PWAVE84_copy_SPDF.columns.difference(['geometry'])
                PWAVE84_copy_SPDF[PWAVE84_copy_SPDF_mask] = PWAVE84_copy_SPDF[PWAVE84_copy_SPDF_mask].mask(PWAVE84_copy_SPDF[PWAVE84_copy_SPDF_mask] < -999, np.nan)
    
                for i in tempcols:
                    minus_tab[i] = PWAVE84_copy_SPDF_mask[i] - PWAVE_copy_SPDF_mask[i]

    
                minus_tab_num_cols = minus_tab.select_dtypes(include='number').columns
                minus_tab[minus_tab_num_cols] = minus_tab[minus_tab_num_cols].clip(lower=0)
                
                PWAVERR_SPDF_mask = PWAVERR_SPDF.columns.difference(['geometry'])
                PWAVERR_SPDF[PWAVERR_SPDF_mask] = minus_tab
                
                
                fill_value = float(WVERR_attr_map['DEF'].iloc[-1])
                num_cols = PWAVERR_SPDF.select_dtypes(include='number').columns
                PWAVERR_SPDF[num_cols] = PWAVERR_SPDF[num_cols].fillna(fill_value)
                lib.write_log('Sample Surge Error (B-A):')
                lib.write_log(str(PWAVERR_SPDF.columns.difference('geometry').head()))
                
                # Find the fully NULL nodes in PSURGE and get the SIDs.
                # remove those features from each feature class
                PWAVE_SPDF_mask = PWAVE_SPDF.columns.difference('geometry')
                PWAVE_SPDF_filtered = PWAVE_SPDF[PWAVE_SPDF_mask]
                badrows = PWAVE_SPDF_filtered[len(WV_attr_map)-1].eq(WV_attr_map.iloc[len(WV_attr_map)]['DEF'])
                
                if (~badrows).sum() > 0:
                    PWAVE_SPDF = PWAVE_SPDF[~badrows]
                    PWAVE84_SPDF = PWAVE84_SPDF[~badrows]
                    PWAVERR_SPDF = PWAVERR_SPDF[~badrows]
                
                lib.write_log('END STEP 2b.')
                step2b_elapsed = math.ceil(monotonic() - step2b_start)
                lib.write_log(f'Full Analysis: {step2b_elapsed} sec elapsed')
                
		##############
		#  	STEP 2c - Attach surge to buildings
		# 	RESULTS:
		#		WSE.SPDF, _WSE.SHP
        step2c_start = monotonic()
        lib.write_log(' ')
        lib.write_log('BEGIN Step 2c. Attach Surge to Buildings')
        surge_attr_map = SWEL_attr_map.copy()
        out_tab = None
        # Get 3NN PSURGE
        lib.write_log('.run 3NN on surge nodes.')
        dfs = []
        for i in range(len(BUILDING_SPDF)):
            row = BUILDING_SPDF.iloc[i]
            # drop geometry column for attributes (mimics @data[this.row,])
            attr_row = row.drop(labels=[BUILDING_SPDF.geometry.name])
            # extract coordinates (mimics @coords[this.row,])
            coord_xy = (row.geometry.x, row.geometry.y)
            res = lib.attachWSELtoBUILDING3(attr_row, coord_xy, PSURGE_SPDF, surge_attr_map)
            dfs.append(res)
        out_tab = pd.concat(dfs, ignore_index=True)
        
        # format out.tab to remove factors and then make all columns numeric
        lib.write_log('.formatting table.')
        out_tab.apply(lambda col: col.astype(str) if col.dtype.name == "category" else col)
        out_tab = out_tab.apply(pd.to_numeric, errors="raise")

        if inputs.use_uncertainty:
            lib.write_log('.get PSURGE ERR.')
            surge_attr_map = SWEL_attr_map.copy()
            out_tab2 = None
            dfs = []
            for i in range(len(BUILDING_SPDF)):
                row = BUILDING_SPDF.iloc[i]
                # drop geometry column for attributes (mimics @data[this.row,])
                attr_row = row.drop(labels=[BUILDING_SPDF.geometry.name])
                # extract coordinates (mimics @coords[this.row,])
                coord_xy = (row.geometry.x, row.geometry.y)
                res = lib.attachWSELtoBUILDING3(attr_row, coord_xy, PSURGERR_SPDF, SWERR_attr_map)
                dfs.append(res)
            out_tab2 = pd.concat(dfs, ignore_index=True)
            
            # format out.tab2 to remove factors and then make all columns numeric
            lib.write_log('.formatting table.')
            out_tab2.apply(lambda col: col.astype(str) if col.dtype.name == "category" else col)
            out_tab2 = out_tab2.apply(pd.to_numeric, errors="raise")
            
        else:
            out_tab2 = None
            
        surge_error_col = SWERR_attr_map.loc[SWERR_attr_map["DESC"] == "surge error", "OUT"].iloc[0]
        out_tab3 = out_tab2[["BID", surge_error_col]]
        out_tab1 = out_tab.merge(out_tab3, on="BID", how="left")
        out_tab1 = out_tab1 = out_tab1.sort_values(by="BID").reset_index(drop=True)
            
        # set building validity
        lib.write_log(".attributing building validity.")
		# find which buildings have good probability of being affected by max event
        tabWET = out_tab1.apply(lambda row: 1 - norm.cdf(lib.getZscore(row["DEMFT"], row["s10000"], row["sx10000"])),axis=1)
        sel = tabWET.index[tabWET >= 0.05].tolist()
        out_tab1.loc[sel, 'VALID'] = 1

        # set building validity
        # find building elevations = -9999
        sel = out_tab1.index[out_tab1["DEMft"] <= -999].tolist()
        out_tab1.loc[sel, 'VALID'] = 0
        
        # build output shapefile
		# no record filtering and no joining, so out points geometry = in points geometry
        out_tab1['geometry'] = BUILDING_SPDF['geometry']
        WSE_SPDF = gpd.GeoDataFrame(out_tab1, geometry='geometry')

        # create a copy of WSE for writing output that converts NA to -99999 so ESRI SHP doesnt 
		# auto-convert NA to 0.
		# Erase copy with the trash collection
        WSE2_SPDF = WSE_SPDF.copy()
        WSE2_SPDF = WSE2_SPDF.fillna(float(SWEL_attr_map.loc[1, "DEF"]))
        
        # write output shapefile
        WSE2_SPDF.to_file(fr'{out_shp_dsn}\{inputs.proj_prefix}_WSE.shp')

        lib.write_log('END STEP 2c.')
        step2c_elapsed = monotonic() - step2c_start
        lib.write_log(f'Full Analysis: {step2c_elapsed} sec elapsed')

		##############
		#  	STEP 2d - Attach waves to buildings
		# 	RESULTS:
		#		WAV.SPDF, _WAV.SHP
  
  
  
  
        ##############
        #  	STEP 3a
        #		Prep data, reduce buildings, assign DDFs
        # 	RESULTS:
        #		FULL.SPDF = wse + wav
        #		VAL.SPDF = reduced dataset
        #		PREP.SPDF, _PREP.SHP
        ##############
  
  
  
  
        ##############
        #  	STEP 4a
        #	Run Monte Carlo simulations
        # 	RESULTS:
        #		pvals, pvals.csv
        ##############
  
  
  
  
        ##############
        #  	STEP 5
        #		create heatmap from RESULTS.SPDF.  Uses the best estimate Building AAL only.
        #		grid value units = $ per acre
        # 	RESULTS:
        # 		kde.grid, _.tif
        ##############
  
  
  
  
        #################
        # end parallel processing
  
  
  
##########################
# End program
##########################
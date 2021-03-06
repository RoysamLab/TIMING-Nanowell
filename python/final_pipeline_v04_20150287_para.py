#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, operator, pdb, subprocess, multiprocessing
import sys, os, time
import numpy
import helper
import time
from final_pipeline_params import *
#from helper import SaveFiles, RunParallel

if __name__ == '__main__':

    ################################################################### This Part is for Code Readers ##############################################

    # Adquisition conditions
    numb_well_per_row = 6 
    num_of_time_decimals = 2
    num_of_block_decimals = 3

    # Directories and Path:
    microscope = 'zeiss'
    data_id = '20150827_MM_01_Z'
    root_path = '/data/shared/mamart51/'
    exe_path= '/data/pdata/ylv2/WorkStation/FTK/bin/exe/'
    data_path = root_path + data_id +'/'
    save_root_path = '/data/pdata/ylv2/results/'
    out_path =  save_root_path + data_id +'RESULTS/'
    param_path = '/data/pdata/ylv2/final_pipeline/parameters/'


    ## Run Flags ##
    ## This has to be 1 at least once for each data set (subfolders)
    saveFileNames = 1 
    ## save filenames and run image to stack should be enabled/disabled at the same time
    runImageToStack = 1
    ##  
    runUnmixing =1
    ##  
    runBackgroundSubstraction =1
    ## If this is 1, make sure the runBackgroundSubstraction has also been 1 at least once 
    runSegmentation = 1
    ##  
    runWellCropping = 1 

    ## Channel Dictionary: ##
    ## change the channel name according to the actual fluophore used in the experiment ##

### Leica Dictionary
    #channel_dict = {"bright_field":"BF",
        #"effectors":"GFP",
        #"targets":"RFP",
        #"death":"CY5",
        #"beads_1":"--",
        #"beads_2":"--"}

##Zeiss Dictionary
    channel_dict = {"bright_field":"c1_ORG",
                    "effectors":"c4_ORG",
                    "targets":"c3_ORG",
                    "death":"c2_ORG",
                    "beads_1":"--",
                    "beads_2":"--"}

    ## Indicate which Channels to Process: ##
    stack_tuple = ("bright_field","effectors","targets","death") ## eg in a time lapse, we wantto stack multiple snap shots together to create a video

    preprocess_tuple = ("effectors","targets")## removing background

    segment_tuple = ("effectors","targets") ## for segmenting

    unmix_tuple = ("targets","effectors") ## assume the first channel leaks into the second one,  removing spectral overlap

    crop_tuple = ("bright_field","death") # Preproces and segment tuple will be segmented, plus this one

    # Analysis
    range_blocks = range(1,501) ## it can be a range or a list

    start_block = 0 
    end_block =500

    numprocessors = 21 
    numprocessorsForCropping = 20

    channel_naming_dict = {"bright_field":"0",
        "effectors":"1",
        "targets":"2",
        "death":"3",
        "beads_1":"4",
        "beads_2":"5"}

    ################################################################### This Part is for Code Readers ##############################################
    if runImageToStack:
       saveFileNames = 1

    # Do a path check
    if not os.path.isdir(exe_path):
        print "executable directory:\n"+ exe_path +"\ndoes not exist"
        sys.exit()
    if not os.path.isdir(root_path):
        print "root directory:\n"+ root_path +"\ndoes not exist"
        sys.exit()
    if saveFileNames:
        if not os.path.isdir(data_path):
            print "data directory:\n"+ data_path +"\ndoes not exist"
            sys.exit()
    if not os.path.isdir(param_path):
        print "parameters directory:\n"+ param_path +"\ndoes not exist"
        sys.exit()
    if not os.path.isdir(save_root_path):
        print "parameters directory:\n"+ save_root_path +"\ndoes not exist"
        sys.exit()

    if not os.path.isdir(out_path):
        os.makedirs(os.path.join(out_path))

    if saveFileNames:
        helper.SaveFiles( data_path, save_root_path, data_id, range_blocks, out_path, stack_tuple, channel_dict, channel_naming_dict, microscope, num_of_time_decimals, num_of_block_decimals )
        file_list_path = os.path.join(save_root_path+data_id+'_FileList/')

########################################## Main Processing Loop ##################################

    block_list = os.listdir(out_path)
    block_list = sorted(block_list)

    end_block = min( end_block, len(block_list) )
    #print "end_block: "+str(end_block)
    block_list = block_list[start_block:end_block]
    #for block_dir in block_list[1]:
    t1 = time.time()
    commandsGlobal = []
    for block_dir in block_list:
        #print 'In Block '+str(block_dir)
        if not os.path.isdir(os.path.join(out_path,block_dir)):
            os.makedirs(os.path.join(out_path,block_dir))

        filename_dict = {}
        for ch in stack_tuple:
            filename_dict[ch] = block_dir +'CH'+channel_naming_dict[ch]+'.tif'

        #### Stack Image Data ####################################
        ompNumThreads = 1 #FIXME is giving an error when reading in parallel
        commands = []
        if runImageToStack:
	    print 'Stacking...'
            for ch in stack_tuple:
                temp = []
                temp.append(os.path.join(exe_path,'image_to_stack'))
                temp.append(os.path.join(file_list_path,'inputfnames_'+block_dir+ '_' +channel_naming_dict[ch]+'.txt'))
                temp.append(os.path.join(out_path,block_dir))
                temp.append(filename_dict[ch])
                temp.append( str(ompNumThreads) )
                #print '\timgToStack, cmd: '+" ".join(temp)

                #subprocess.call(temp)
                temp = " ".join(temp)
                commandsGlobal.append(temp)
                #commands.append(temp)
            #helper.RunParallel(commands,1)
    helper.RunParallel(commandsGlobal,numprocessors)
    print "1-STACK TIME: " +str(time.time() - t1)

    t1 = time.time()
    commandsGlobal = []
    for block_dir in block_list:
        filename_dict = {}
        for ch in stack_tuple:
            filename_dict[ch] = block_dir +'CH'+channel_naming_dict[ch]+'.tif'
      ###### spectral unmixing ############################################################
        ompNumThreads = 11
        umx_prefix = 'umx_'
        commands = []
        if runUnmixing:
	    print 'Unmixing...'
            temp = []
            temp.append( os.path.join(exe_path,'unmix16') )
            temp.append( os.path.join(out_path,block_dir,filename_dict[unmix_tuple[0]]) )
            temp.append( os.path.join(out_path,block_dir,filename_dict[unmix_tuple[1]]) )
            temp.append( os.path.join(out_path,block_dir,umx_prefix + filename_dict[unmix_tuple[0]]) )
            temp.append( os.path.join(out_path,block_dir,umx_prefix + filename_dict[unmix_tuple[1]]) )
            temp.append( os.path.join(param_path,str(data_id)+'_mixing_matrix.txt' ) )
            temp.append( os.path.join(out_path,block_dir,'a_newMixing.tif' ) )
            temp.append( str(ompNumThreads) )

            #print '\tunmix, cmd: '+" ".join(temp)

            #subprocess.call(temp)
            temp = " ".join(temp)
            commandsGlobal.append(temp)
            #commands.append(temp)
        #helper.RunParallel(commands,2)
    helper.RunParallel(commandsGlobal,numprocessors)
    print "2-UNMIX TIME: " +str(time.time() - t1)

    t1 = time.time()
    commandsGlobal = []
    for block_dir in block_list:
        filename_dict = {}
        for ch in stack_tuple:
            filename_dict[ch] = block_dir +'CH'+channel_naming_dict[ch]+'.tif'
      ##### background subtraction ############################################################
        ompNumThreads = 11
        bg_param = 40
        bg_prefix = 'bg_'
        commands = []
        if runBackgroundSubstraction:
	    print 'Background substracting...'
            for ch in preprocess_tuple:
                temp = []
                temp.append(os.path.join(exe_path,'background_subtraction'))
                if ch in unmix_tuple:
                    temp.append( os.path.join(out_path,block_dir,umx_prefix + filename_dict[ch]) )
                else:
                    temp.append( os.path.join(out_path,block_dir,filename_dict[ch]) )
                temp.append( os.path.join(out_path,block_dir,bg_prefix + filename_dict[ch]) )
                temp.append( str(bg_param) )
                temp.append( str(ompNumThreads) )
                #print '\tbacksubs, cmd: '+" ".join(temp)

                #subprocess.call(temp)
                temp = " ".join(temp)
                commandsGlobal.append(temp)
                #commands.append(temp)
        #helper.RunParallel(commands,2)
    #print "here"
    helper.RunParallel(commandsGlobal,numprocessors)
    print "3-BS TIME: " +str(time.time() - t1)

    t1 = time.time()
    commandsGlobal = []
    for block_dir in block_list:
        filename_dict = {}
        for ch in stack_tuple:
            filename_dict[ch] = block_dir +'CH'+channel_naming_dict[ch]+'.tif'
      ####### mixture segmentation #####################################################################################
        ompNumThreads = 11
        clean_prefix = 'bin_'
        commands = []
        if runSegmentation:
	    print 'Segmenting...'
            for ch in segment_tuple:
                temp = []
                temp.append(os.path.join(exe_path,'mixture_segment'))
                temp.append(os.path.join(out_path,block_dir,bg_prefix + filename_dict[ch]))
                temp.append(os.path.join(out_path,block_dir,clean_prefix + filename_dict[ch]))
		if ch== "effectors":
		    temp.append(os.path.join(param_path,str(data_id)+'_segmentation_paramters_eff.txt'))
		if ch== "targets":
		    temp.append(os.path.join(param_path,str(data_id)+'_segmentation_paramters_tar.txt'))
                temp.append( str(ompNumThreads) )
                #print '\tsegment, cmd: '+" ".join(temp)
                #subprocess.call(temp)
                temp = " ".join(temp)
                commandsGlobal.append(temp)
                #commands.append(temp)
        #helper.RunParallel(commands,2)
    helper.RunParallel(commandsGlobal,numprocessors)
    print "4-SEGM TIME: " +str(time.time() - t1)

    t1 = time.time()
    commandsGlobal = []
    for block_dir in block_list:
        filename_dict = {}
        for ch in stack_tuple:
            filename_dict[ch] = block_dir +'CH'+channel_naming_dict[ch]+'.tif'
      ####### well cropping #####################################################################################
        ompNumThreads = 3
        commands = []
        if runWellCropping:
	    print 'Cropping...'
            if not os.path.isdir(os.path.join(out_path,block_dir,'crops')):
                os.makedirs( os.path.join(out_path,block_dir,'crops') )
            if not os.path.isdir(os.path.join(out_path,block_dir,'features')):
                os.makedirs( os.path.join(out_path,block_dir,'features') )
            temp = []
            temp.append(os.path.join(exe_path,'wellDetection'))
            temp.append(os.path.join(param_path,str(data_id)+'_P_rom.tif'))
            temp.append(os.path.join(param_path,str(data_id)+'_P_squ.tif'))
            temp.append(os.path.join(out_path,block_dir,'crops' ))
            temp.append('0' )  #starting slice
            temp.append( str(numb_well_per_row) ) #number of wells in each column/row
            temp.append( str(ompNumThreads) )
            for ch in crop_tuple:
                temp.append(os.path.join(out_path,block_dir, block_dir+'CH'+channel_naming_dict[ch]+'.tif' ))
            for ch in segment_tuple:
                temp.append(os.path.join(out_path,block_dir, 'bin_'+ block_dir+'CH'+channel_naming_dict[ch]+'.tif' ))
            for ch in preprocess_tuple:
                temp.append(os.path.join(out_path,block_dir, 'bg_'+ block_dir+'CH'+channel_naming_dict[ch]+'.tif' ))

            #print temp
            #subprocess.call(temp)
            temp = " ".join(temp)
            commandsGlobal.append(temp)
            #commands.append(temp)
        #helper.RunParallel(commands,2)
    helper.RunParallel(commandsGlobal,numprocessorsForCropping)
    print "5-CROP TIME: " +str(time.time() - t1)









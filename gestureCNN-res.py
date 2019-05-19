#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  6 01:01:43 2017

@author: abhisheksingh
"""

from keras.models import Sequential, Model
from keras.layers import Dense, Dropout, Activation, Flatten, Input, add
from keras.layers import Conv2D, MaxPooling2D, ZeroPadding2D, GlobalAveragePooling2D
from keras.callbacks import History, ModelCheckpoint
from keras.applications.mobilenet_v2 import MobileNetV2
from keras.optimizers import SGD,RMSprop,adam
from keras.utils import np_utils

from keras import backend as K
if K.backend() == 'tensorflow':
    import tensorflow
    #K.set_image_dim_ordering('tf')
else:
    import theano
    #K.set_image_dim_ordering('th')

'''Ideally we should have changed image dim ordering based on Theano or Tensorflow, but for some reason I get following error when I switch it to 'tf' for Tensorflow.
	However, the outcome of the prediction doesnt seem to get affected due to this and Tensorflow gives me similar result as Theano.
	I didnt spend much time on this behavior, but if someone has answer to this then please do comment and let me know.
    ValueError: Negative dimension size caused by subtracting 3 from 1 for 'conv2d_1/convolution' (op: 'Conv2D') with input shapes: [?,1,200,200], [3,3,200,32].
'''
K.set_image_dim_ordering('th')
# K.set_image_dim_ordering('tf')  # channels_last

import numpy as np
#import matplotlib.pyplot as plt
import os

from PIL import Image
# SKLEARN
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
import json

import cv2
import matplotlib
#matplotlib.use("TkAgg")
from matplotlib import pyplot as plt

# input image dimensions
img_rows, img_cols = 200, 200
# img_rows, img_cols = 224, 224

# number of channels
# For grayscale use 1 value and for color images use 3 (R,G,B channels)
img_channels = 1

# Batch_size to train
batch_size = 32

# Number of epochs to train (change it accordingly)
nb_epoch = 25

# Total number of convolutional filters to use
nb_filters = 32
# Max pooling
nb_pool = 2
# Size of convolution kernel
nb_conv = 3

#%%
#  data
path = "./"
path1 = "./gestures"    #path of folder of images

## Path2 is the folder which is fed in to training model
path2 = './imgfolder'

WeightFileName = ["ori_4015imgs_weights.hdf5","bw_4015imgs_weights.hdf5","bw_2510imgs_weights.hdf5","./bw_weight.hdf5","./final_c_weights.hdf5","./semiVgg_1_weights.hdf5","/new_wt_dropout20.hdf5","./weights-CNN-gesture_skinmask.hdf5"]

# outputs
# output = ["OK", "NOTHING","PEACE", "PUNCH", "STOP"]
output = ["ONE_LEFT", "TWO_LEFT", "THREE_LEFT", "FOUR_LEFT", "FIVE_LEFT", "OK_LEFT", "FIST_LEFT", \
          "ONE_RIGHT", "TWO_RIGHT", "THREE_RIGHT", "FOUR_RIGHT", "FIVE_RIGHT", "OK_RIGHT", "FIST_RIGHT", \
          "NOTHING"]

## Number of output classes (change it accordingly)
## eg: In my case I wanted to predict 4 types of gestures (Ok, Peace, Punch, Stop)
## NOTE: If you change this then dont forget to change Labels accordingly
nb_classes = len(output)

jsonarray = {}

#%%
def update(plot):
    global jsonarray
    h = 450
    y = 30
    w = 45
    font = cv2.FONT_HERSHEY_SIMPLEX

    #plot = np.zeros((512,512,3), np.uint8)
    
    #array = {"OK": 65.79261422157288, "NOTHING": 0.7953541353344917, "PEACE": 5.33270463347435, "PUNCH": 0.038031660369597375, "STOP": 28.04129719734192}
    
    for items in jsonarray:
        mul = (jsonarray[items]) / 100
        #mul = random.randint(1,100) / 100
        cv2.line(plot,(0,y),(int(h * mul),y),(255,0,0),w)
        cv2.putText(plot,items,(0,y+5), font , 0.7,(0,255,0),2,1)
        y = y + w + 30

    return plot

# This function can be used for converting colored img to Grayscale img
# while copying images from path1 to path2
def convertToGrayImg(path1, path2):
    listing = os.listdir(path1)
    for file in listing:
        if file.startswith('.'):
            continue
        img = Image.open(path1 +'/' + file)
        #img = img.resize((img_rows,img_cols))
        grayimg = img.convert('L')
        grayimg.save(path2 + '/' +  file, "PNG")

def modlistdir(path):
    listing = os.listdir(path)
    retlist = []
    for name in listing:
        #This check is to ignore any hidden files/folders
        if name.startswith('.'):
            continue
        retlist.append(name)
    return retlist

def residual_block(block_input, output_channel=64, kernel_size=(3, 3)):
    conv_1 = Conv2D(output_channel, (3, 3), padding='same', activation='relu')(block_input)
    conv_2 = Conv2D(output_channel, (3, 3), padding='same')(conv_1)
    res_add = add([conv_2, block_input])
    res_output = Activation('relu')(res_add)
    return res_output

# Load CNN model
def loadCNN(wf_index):
    global get_output
    model_input = Input(shape=(img_channels, img_rows, img_cols))
    conv_1 = Conv2D(64, (3, 3), padding='valid', activation='relu')(model_input)
    max_pool_1 = MaxPooling2D(pool_size=(2, 2))(conv_1)
    conv_1_1 = Conv2D(64, (3, 3), padding='valid', activation='relu')(max_pool_1)
    max_pool_1_1 = MaxPooling2D(pool_size=(2, 2))(conv_1_1)
    # residual block
    res_1 = residual_block(max_pool_1_1)
    conv_2 = Conv2D(128, (3, 3), activation='relu')(res_1)
    max_pool_2 = MaxPooling2D(pool_size=(2, 2))(conv_2)
    res_2 = residual_block(conv_2, output_channel=128)
    conv_3 = Conv2D(256, (3, 3), activation='relu')(res_2)
    max_pool_3 = MaxPooling2D(pool_size=(2, 2))(conv_3)
    conv_4 = Conv2D(256, (3, 3), activation='relu')(max_pool_3)
    # maxpool = MaxPooling2D(pool_size=(nb_pool, nb_pool))(conv_2)
    global_avg_pool = GlobalAveragePooling2D()(conv_4)
    # dropout_1 = Dropout(0.5)(maxpool)
    # flatten_output = Flatten()(dropout_1)
    # dense_1 = Dense(128, activation='relu')(global_avg_pool)
    # dropout_2 = Dropout(0.5)(dense_1)
    output = Dense(nb_classes, activation='softmax')(global_avg_pool)

    '''
    # model.add(Conv2D(nb_filters, (nb_conv, nb_conv)))
    # convout2 = Activation('relu')
    # model.add(convout2)
    # model.add(MaxPooling2D(pool_size=(nb_pool, nb_pool)))
    # model.add(Dropout(0.5))

    # model.add(Flatten())
    # model.add(Dense(128))
    # model.add(Activation('relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(nb_classes))
    # model.add(Activation('softmax'))
    
    # model.add(ZeroPadding2D((1,1),input_shape=(img_channels, img_rows, img_cols)))
    # model.add(Conv2D(nb_filters , (nb_conv, nb_conv), activation='relu'))
    # #model.add(ZeroPadding2D((1,1)))
    # #model.add(Conv2D(nb_filters , (nb_conv, nb_conv), activation='relu'))
    # model.add(MaxPooling2D(pool_size=(nb_pool, nb_pool)))
    # model.add(Dropout(0.2))
    # 
    # #model.add(ZeroPadding2D((1,1)))
    # model.add(Conv2D(nb_filters , (nb_conv, nb_conv), activation='relu'))
    # #model.add(ZeroPadding2D((1,1)))
    # model.add(MaxPooling2D(pool_size=(nb_pool, nb_pool)))
    # ##
    # #model.add(Conv2D(nb_filters , (nb_conv, nb_conv), activation='relu'))
    # #model.add(MaxPooling2D(pool_size=(nb_pool, nb_pool), strides=(2,2)))
    # 
    # model.add(Dropout(0.3))
    # model.add(Flatten())
    # ###
    # #model.add(Dense(128))
    # #model.add(Activation('relu'))
    # #model.add(Dropout(0.5))

    # model.add(Dense(256))
    # model.add(Activation('relu'))
    # model.add(Dropout(0.5))
    # model.add(Dense(nb_classes))
    # model.add(Activation('softmax'))
    '''
    
    #sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model = Model(inputs=model_input, outputs=output)
    model.compile(loss='categorical_crossentropy', optimizer='adadelta', metrics=['accuracy'])
    
    
    # Model summary
    model.summary()
    # Model conig details
    model.get_config()
    
    #from keras.utils import plot_model
    #plot_model(model, to_file='new_model.png', show_shapes = True)
    

    if wf_index >= 0:
        #Load pretrained weights
        fname = WeightFileName[int(wf_index)]
        print("loading ", fname)
        model.load_weights(fname)
    
    layer = model.layers[-1]
    get_output = K.function([model.layers[0].input, K.learning_phase()], [layer.output,])
    
    
    return model

# This function does the guessing work based on input images
def guessGesture(model, img):
    global output, get_output, jsonarray
    #Load image and flatten it
    image = np.array(img).flatten()
    
    # reshape it
    image = image.reshape(img_channels, img_rows,img_cols)
    
    # float32
    image = image.astype('float32') 
    
    # normalize it
    image = image / 255
    
    # reshape for NN
    rimage = image.reshape(1, img_channels, img_rows, img_cols)
    
    # Now feed it to the NN, to fetch the predictions
    #index = model.predict_classes(rimage)
    #prob_array = model.predict_proba(rimage)
    
    prob_array = get_output([rimage, 0])[0]
    
    #print prob_array
    
    d = {}
    i = 0
    for items in output:
        d[items] = prob_array[0][i] * 100
        i += 1
    
    # Get the output with maximum probability
    import operator
    
    guess = max(d.items(), key=operator.itemgetter(1))[0]
    prob  = d[guess]

    if prob > 60.0:
        #print(guess + "  Probability: ", prob)

        #Enable this to save the predictions in a json file,
        #Which can be read by plotter app to plot bar graph
        #dump to the JSON contents to the file
        
        #with open('gesturejson.txt', 'w') as outfile:
        #    json.dump(d, outfile)
        jsonarray = d
                
        return output.index(guess)

    else:
        return 1

#%%
def initializers():
    imlist = modlistdir(path2)
    
    image1 = np.array(Image.open(path2 +'/' + imlist[0])) # open one image to get size
    #plt.imshow(im1)
    
    m, n = image1.shape[0:2] # get the size of the images
    total_images = len(imlist) # get the 'total' number of images
    
    # create matrix to store all flattened images
    # immatrix = np.array([np.array(Image.open(path2+ '/' + images).convert('RGB')).flatten()
    immatrix = np.array([np.array(Image.open(path2+ '/' + images).convert('L')).flatten()
                         for images in sorted(imlist)], dtype='f')
    
    print(immatrix.shape)
    
    input("Press any key")
    
    #########################################################
    ## Label the set of images per respective gesture type.
    ##
    label=np.ones((total_images,), dtype=int)
    
    samples_per_class = int(total_images / nb_classes)
    print("samples_per_class - ", samples_per_class)
    s = 0
    r = int(samples_per_class)
    for classIndex in range(nb_classes):
        label[s:r] = classIndex
        s = r
        r = s + samples_per_class
    
    '''
    # eg: For 301 img samples/gesture for 4 gesture types
    label[0:301]=0
    label[301:602]=1
    label[602:903]=2
    label[903:]=3
    '''
    
    data,Label = shuffle(immatrix,label, random_state=2)
    train_data = [data,Label]
     
    (X, y) = (train_data[0],train_data[1])
     
    # Split X and y into training and testing sets
     
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=4)
     
    X_train = X_train.reshape(X_train.shape[0], img_channels, img_rows, img_cols)
    X_test = X_test.reshape(X_test.shape[0], img_channels, img_rows, img_cols)
     
    X_train = X_train.astype('float32')
    X_test = X_test.astype('float32')
     
    # normalize
    X_train /= 255
    X_test /= 255
     
    # convert class vectors to binary class matrices
    Y_train = np_utils.to_categorical(y_train, nb_classes)
    Y_test = np_utils.to_categorical(y_test, nb_classes)
    return X_train, X_test, Y_train, Y_test

def trainModel(model):

    # Split X and y into training and testing sets
    X_train, X_test, Y_train, Y_test = initializers()

    print('shapes: xtrain: {} | xtest: {} | ytrain: {}, ytest: {}'.format(X_train.shape, X_test.shape, Y_train.shape, Y_test.shape))
    # Now start the training of the loaded model
    if not os.path.exists('checkpoint'):
        os.makedirs('checkpoint')
    checkpointer = ModelCheckpoint(filepath=os.path.join('checkpoint', 'weights.{epoch:02d}.hdf5'), verbose=1, save_weights_only=True)
    hist_recorder = History()

    hist = model.fit(X_train, Y_train, batch_size=batch_size, epochs=nb_epoch, verbose=1, validation_split=0.2, callbacks=[checkpointer, hist_recorder])

    visualizeHis(hist)

    ans = input("Do you want to save the trained weights - y/n ?")
    if ans == 'y':
        filename = input("Enter file name - ")
        fname = path + str(filename) + ".hdf5"
        model.save_weights(fname,overwrite=True)
    else:
        model.save_weights("newWeight.hdf5",overwrite=True)

    # Save model as well
    # model.save("newModel.hdf5")
#%%

def visualizeHis(hist):
    # visualizing losses and accuracy

    train_loss=hist.history['loss']
    val_loss=hist.history['val_loss']
    train_acc=hist.history['acc']
    val_acc=hist.history['val_acc']
    xc=range(nb_epoch)

    plt.figure(1,figsize=(7,5))
    plt.plot(xc,train_loss)
    plt.plot(xc,val_loss)
    plt.xlabel('num of Epochs')
    plt.ylabel('loss')
    plt.title('train_loss vs val_loss')
    plt.grid(True)
    plt.legend(['train','val'])
    #print plt.style.available # use bmh, classic,ggplot for big pictures
    #plt.style.use(['classic'])

    plt.figure(2,figsize=(7,5))
    plt.plot(xc,train_acc)
    plt.plot(xc,val_acc)
    plt.xlabel('num of Epochs')
    plt.ylabel('accuracy')
    plt.title('train_acc vs val_acc')
    plt.grid(True)
    plt.legend(['train','val'],loc=4)

    plt.show()

#%%
def visualizeLayers(model, img, layerIndex):
    imlist = modlistdir('./imgs')
    if img <= len(imlist):
        
        image = np.array(Image.open('./imgs/' + imlist[img - 1]).convert('L')).flatten()
        
        ## Predict
        guessGesture(model,image)
        
        # reshape it
        image = image.reshape(img_channels, img_rows,img_cols)
        
        # float32
        image = image.astype('float32')
        
        # normalize it
        image = image / 255
        
        # reshape for NN
        input_image = image.reshape(1, img_channels, img_rows, img_cols)
    else:
        X_train, X_test, Y_train, Y_test = initializers()
        
        # the input image
        input_image = X_test[:img+1]
    
    
    
        
    # visualizing intermediate layers
    #output_layer = model.layers[layerIndex].output
    #output_fn = theano.function([model.layers[0].input], output_layer)
    #output_image = output_fn(input_image)
    
    if layerIndex >= 1:
        visualizeLayer(model,img,input_image, layerIndex)
    else:
        tlayers = len(model.layers[:])
        print("Total layers - {}".format(tlayers))
        for i in range(1,tlayers):
             visualizeLayer(model,img, input_image,i)

#%%
def visualizeLayer(model, img, input_image, layerIndex):

    layer = model.layers[layerIndex]
    
    get_activations = K.function([model.layers[0].input, K.learning_phase()], [layer.output,])
    activations = get_activations([input_image, 0])[0]
    output_image = activations
    
    
    ## If 4 dimensional then take the last dimension value as it would be no of filters
    if output_image.ndim == 4:
        # Rearrange dimension so we can plot the result
        o1 = np.rollaxis(output_image, 3, 1)
        output_image = np.rollaxis(o1, 3, 1)
        
        print("Dumping filter data of layer{} - {}".format(layerIndex,layer.__class__.__name__))
        filters = len(output_image[0,0,0,:])
        
        fig=plt.figure(figsize=(8,8))
        # This loop will plot the 32 filter data for the input image
        for i in range(filters):
            ax = fig.add_subplot(6, 6, i+1)
            #ax.imshow(output_image[img,:,:,i],interpolation='none' ) #to see the first filter
            ax.imshow(output_image[0,:,:,i],'gray')
            #ax.set_title("Feature map of layer#{} \ncalled '{}' \nof type {} ".format(layerIndex,
            #                layer.name,layer.__class__.__name__))
            plt.xticks(np.array([]))
            plt.yticks(np.array([]))
        plt.tight_layout()
        #plt.show()
        fig.savefig("img_" + str(img) + "_layer" + str(layerIndex)+"_"+layer.__class__.__name__+".png")
        #plt.close(fig)
    else:
        print("Can't dump data of this layer{}- {}".format(layerIndex, layer.__class__.__name__))



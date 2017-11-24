import random
import shutil,json
from keras import callbacks
import os, sys
import numpy as np
import csv
#import preprocess
from preprocess import CAPTION_LEN, ENG_SOS, ENG_EOS, ENG_EXTRA, ENG_NONE, DIR_IMAGES, OUTENCODINGGLOVE, GITBRANCHPREFIX
from preprocess import  embeddingIndexRef, imageToVec, word2embd, embdToWord, captionToVec, get_image_caption, build_vocab, build_dataset, build_gloveVocab, get_image_fname, word2embd, WordToWordDistance, wordToEncode
from preprocess import createDirs
from model import build_model


CLABEL= 'vgg16_onehot'
state = {'epochs':1000,'inepochs':10,'batch_size':3,'super_batch':10,'val_batch':2}

MFNAME= GITBRANCHPREFIX+'model_'+CLABEL+'.dat'
_MFNAME= GITBRANCHPREFIX+'model_'+CLABEL+'.dat.bak'
ELOGS = GITBRANCHPREFIX+CLABEL + "_logs.txt"
STATE = GITBRANCHPREFIX+'state_'+CLABEL+'.txt'
model = None

epochLogHistory = []
def flushLogEpoch():
    global epochLogHistory
    if not os.path.exists(ELOGS):
        with open(ELOGS,"w") as f:
            wr = csv.writer(f)
            # Iteration is row id
            wr.writerow(["EpochId","Acc","Loss","Val Acc","Val loss"])
    if len(epochLogHistory)>0:
        with open(ELOGS,"ab") as f:
            wr = csv.writer(f)
            #wr.writerow([])
            for h in epochLogHistory:
                wr.writerow(h)
            epochLogHistory = []
            print "ELogs written"
    
def loadstate():
    global model
    global state
    if os.path.exists(MFNAME):
        model.load_weights(MFNAME)
        print "Weights Loaded"
    if os.path.exists(STATE):
        with open(STATE) as f:
            state = json.load(f)
            print "State Loaded"


def savestate():
    global model
    try:
        pass
    finally:
        tname = _MFNAME
        model.save_weights(tname)
        shutil.copy2(tname, MFNAME)
        os.remove(tname)
        print "Weights Saved"
        with open(STATE,'w') as f:
            json.dump(state,f)
            print "State Saved"

class ModelCallback(callbacks.Callback):
 
    def on_epoch_end(self, epoch, logs={}):
        #state['epochs']-=1
        #savestate()
        print logs.keys()
        epochLogHistory.append([epoch,logs['acc'],logs['loss'],logs['val_acc'],logs['val_loss'],logs['sentence_distance'],logs['val_sentence_distance']])
        return

def loadmodel():
    global model
    model = build_model(CAPTION_LEN)
    loadstate()

def prepare_feedkeras(trainset):
    trainX1 = []
    trainX2 = []
    trainY = []
    i = 0
    # Glove
    we_sos = [word2embd(ENG_SOS)]
    we_eos = [word2embd(ENG_EOS)]
    # One Hot
    we_eosOH = [wordToEncode(ENG_EOS,encodeType="onehot")]
    #print we_sos
    #print we_eos
    print "Arranging Trainset"
    while i < len(trainset):
        image = trainset[i][0]
        # Glove
        capS =  we_sos + trainset[i][1] 
        outWord = None
        # Chose according to out embedding
        if OUTENCODINGGLOVE:
            outWord = trainset[i][1]
        else:
            # one hot
            outWord = trainset[i][2]
        capE =  outWord + we_eosOH

        #print "%d ; %d " %(len(capS),len(capE))
        trainX1.append( capS )
        trainX2.append( image )
        trainY.append( capE )
        if False and i==0:
            print "capS %s " % capS
            print "capE %s " % capE
            print "Image %s" % str(image)

        i+=1
    trainX = [np.array( trainX1 ), np.array( trainX2 )]
    trainY = np.array(trainY)
    return (trainX,trainY)

def train_model(trainvalset):
    #print [x for x in train_generator(trainset)]
    #return
    #model.fit_generator(train_generator(trainset),steps_per_epoch=20,epochs=30,verbose=2)
    (trainX,trainY) = prepare_feedkeras(trainvalset[0])
    valset = prepare_feedkeras(trainvalset[1])
    print "Attempt to Fit Data"
    inEpochs = state['inepochs']
    #print "Train X Shape %s " % str(np.shape(trainX))
    print "Train Y Shape %s " % str(np.shape(trainY))

    model.fit(x=trainX,y=trainY,batch_size=state['batch_size'],epochs=inEpochs, validation_data=valset, verbose=2, callbacks=[ModelCallback()])
    print "Model Fit"

def train(lst):
    MX = state['epochs']
    for it in range(MX):
        dataset = build_dataset(lst, state['super_batch'],state['val_batch'],outerepoch=it)
        print "Outer Iteration %3d of %3d " % (it+1,MX)
        train_model(dataset)
        state['epochs']-=1
        savestate()
        flushLogEpoch()

def wordFromOutModel(embWord):
    # Return (word,acc_mertrics)
    if OUTENCODINGGLOVE:
        return embdToWord(newWordE)
    else:
        # return argmax word
        ind = np.argmax(embdToWord)
        return (v_ind2word[ind], embdToWord[ind])

def predict_model(lst,_ids):
    imgVecs = np.array([imageToVec(_id) for _id in _ids])
    fnames = [get_image_fname(_id) for _id in _ids]
    for fname in fnames:
        print "Predicting for Image %s " % fname
    l = 0
    cnt = len(_ids)
    _capS = np.array([ [word2embd(ENG_SOS)] + ([word2embd(ENG_NONE)] * CAPTION_LEN) ] * cnt)
    print np.shape(_capS)
    strCap = [""]*cnt
    #CAPTION_LEN = 2
    while l < CAPTION_LEN:
        _newCapS = model.predict([_capS,imgVecs])
        _newWord = [newCapS[l] for newCapS in _newCapS]
        print "Got Update Shape %s " % str(np.shape(_newWord))
        for j,newWordE in enumerate(_newWord):
            newWord,metrics = wordFromOutModel(newWordE)
            _capS[j][l+1] = wordToEncode(newWord)
            print "NWord %s\tMetrics= %f" % (newWord,metrics)
            strCap[j] = "%s %s" % (strCap[j],newWord)
            print strCap[j]
        l+=1
        
        #if newWord == ENG_EOS:
        #    break
        #for j in range(cnt):
        #    capS[j] = "%s %s"
        #capS = "%s %s" % (capS, newWord)
        #print newCapS

    for j,out in enumerate(strCap):
        print "eog %s" % (fnames[j])
        print "Observed : %s " % strCap[j]
        actualC = lst[_ids[j]]
        print "Actual   : %s " % actualC
        print [WordToWordDistance(a,b) for a,b in zip(strCap[j],actualC)]

    
def predict(lst,_ids):
    if type(_ids) == type(0):
        l = os.listdir(DIR_IMAGES)
        cnt = _ids
        _ids = []
        for j in range(cnt):
            _ids.append(random.choice(l))
        _ids = [int(fn.split("_")[-1].split(".")[0]) for fn in _ids]
    predict_model(lst,_ids)

def run():
    build_gloveVocab() 
    lst = build_vocab()
    loadmodel()
    if len(sys.argv) < 3:
        train(lst)
    elif len(sys.argv)== 3 and '-predict' == sys.argv[1]:
        predict(lst,[int(x) for x in sys.argv[2].split(",")])
    elif len(sys.argv)== 3 and '-prandom' == sys.argv[1]:
        predict(lst,int(sys.argv[2]))
    else:
        print "Invalid Argument"
if __name__ == '__main__':
    createDirs()
    run()

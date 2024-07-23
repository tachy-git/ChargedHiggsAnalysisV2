#!/usr/bin/env/python
import os
import argparse
import logging

import torch
import ROOT
from sklearn.utils import shuffle
from itertools import product

from torch_geometric.loader import DataLoader
from Preprocess import GraphDataset, rtfileToDataList

parser = argparse.ArgumentParser()
parser.add_argument("--signal", required=True, type=str, help="signal")
parser.add_argument("--background", required=True, type=str, help="background")
parser.add_argument("--channel", required=True, type=str, help="channel")
parser.add_argument("--pilot", action="store_true", default=False, help="pilot mode")
parser.add_argument("--debug", action="store_true", default=False, help="debug mode")
args = parser.parse_args()

# check arguments
if args.channel not in ["Skim1E2Mu", "Skim3Mu", "Combined"]:
    raise ValueError(f"Invalid channel {args.channel}")
if args.signal not in ["MHc-100_MA-95", "MHc-130_MA-90", "MHc-160_MA-85"]:
    raise ValueError(f"Invalid signal {args.signal}")
if args.background not in ["nonprompt", "diboson", "ttZ"]:
    raise ValueError(f"Invalid background {args.background}")

logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
WORKDIR = os.environ["WORKDIR"]

#### load dataset
maxSize = 10000 if args.pilot else -1
maxSizeForEra = {
    "2016preVFP": int(maxSize / 7),
    "2016postVFP": int(maxSize / 7),
    "2017": int(maxSize * (2/7)),
    "2018": int(maxSize * (3/7))
}
logging.debug(maxSizeForEra)
if args.channel == "Combined":
    ## Load signal data
    sigDataList = []
    bkgDataList = []
    for era, channel in product(["2016preVFP", "2016postVFP", "2017", "2018"], ["Skim1E2Mu", "Skim3Mu"]):
        rt = ROOT.TFile.Open(f"dataset/{era}/{channel}/DataPreprocess_TTToHcToWAToMuMu_{args.signal}.root")
        sigDataList += rtfileToDataList(rt, isSignal=True, era=era, maxSize=maxSizeForEra[era])
        rt.Close()

        rt = ROOT.TFile.Open(f"dataset/{era}/{channel}/DataPreprocess_{args.background}.root")
        bkgDataList += rtfileToDataList(rt, isSignal=False, era=era, maxSize=maxSizeForEra[era])
        rt.Close()
    sigDataList = shuffle(sigDataList, random_state=42)
    bkgDataList = shuffle(bkgDataList, random_state=42)
else:
    sigDataList = []
    bkgDataList = []
    for era in ["2016preVFP", "2016postVFP", "2017", "2018"]:
        rt = ROOT.TFile.Open(f"dataset/{era}/{args.channel}/DataPreprocess_TTToHcToWAToMuMu_{args.signal}.root")
        sigDataList += rtfileToDataList(rt, isSignal=True, era=era, maxSize=maxSizeForEra[era])
        rt.Close()

        rt = ROOT.TFile.Open(f"dataset/{era}/{args.channel}/DataPreprocess_{args.background}.root")
        bkgDataList += rtfileToDataList(rt, isSignal=False, era=era, maxSize=maxSizeForEra[era])
        rt.Close()
    sigDataList = shuffle(sigDataList, random_state=42)
    bkgDataList = shuffle(bkgDataList, random_state=42)
logging.info("Finished loading dataset")
logging.info(f"Signal: {len(sigDataList)} events")
logging.info(f"Background: {len(bkgDataList)} events")
dataList = shuffle(sigDataList+bkgDataList, random_state=42)

trainset = GraphDataset(dataList[:int(len(dataList)*0.4)])
validset = GraphDataset(dataList[int(len(dataList)*0.4):int(len(dataList)*0.5)])
testset  = GraphDataset(dataList[int(len(dataList)*0.5):])

baseDir = f"{WORKDIR}/ParticleNet/dataset/{args.channel}__"
if args.pilot:
    baseDir += "pilot__"
logging.info(f"Saving dataset to {baseDir}")
os.makedirs(baseDir, exist_ok=True)
torch.save(trainset, f"{baseDir}/{args.signal}_vs_{args.background}_train.pt")
torch.save(validset, f"{baseDir}/{args.signal}_vs_{args.background}_valid.pt")
torch.save(testset, f"{baseDir}/{args.signal}_vs_{args.background}_test.pt")
logging.info("Finished saving dataset")

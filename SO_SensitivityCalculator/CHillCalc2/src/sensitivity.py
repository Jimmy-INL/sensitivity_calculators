#python Version 2.7.2
import numpy   as np
import physics as ph
import noise   as ns
import units   as un

class Sensitivity:
    def __init__(self, log, exp, corr=True):
        self.__ph   = ph.Physics()
        self.__nse  = ns.Noise()
        self.__exp  = exp
        self.__corr = corr

    #***** Public Methods *****
    def Popt(self, elemArr, emissArr, effArr, tempArr, freqs):
        effArr  = np.insert(effArr, len(effArr), [1. for f in freqs], axis=0); effArr = np.array(effArr).astype(np.float)
        return np.sum([np.trapz(self.__ph.bbPowSpec(freqs, tempArr[i], emissArr[i]*np.prod(effArr[i+1:], axis=0)), freqs) for i in range(len(elemArr))])

    def NEPph(self, elemArr, emissArr, effArr, tempArr, freqs, ch=None):
        effArr  = np.insert(effArr, len(effArr), [1. for f in freqs], axis=0); effArr = np.array(effArr).astype(np.float)
        if ch: corrs = True
        else:  corrs = False
        powInts = np.array([self.__ph.bbPowSpec(freqs, tempArr[i], emissArr[i]*np.prod(effArr[i+1:], axis=0)) for i in range(len(elemArr))])
        if corrs: NEP_ph, NEP_pharr = self.__nse.photonNEP(powInts, freqs, elemArr, (ch.pixSize/(ch.Fnumber*self.__ph.lamb(ch.bandCenter.getAvg()))))
        else:     NEP_ph, NEP_pharr = self.__nse.photonNEP(powInts, freqs)
        return NEP_ph, NEP_pharr

    def NEPbolo(self, cumPower, det):
        if 'NA' in str(det.psat): return self.__nse.bolometerNEP(det.psatFact*cumPower, det.n, det.Tc, det.Tb)
        else:                     return self.__nse.bolometerNEP(det.psat,              det.n, det.Tc, det.Tb)    
    
    def NEPrd(self, cumPower, det):
        if   'NA' in str(det.nei):   return 'NA'
        elif 'NA' in str(det.boloR): return 'NA'
        elif 'NA' in str(det.psat):  return self.__nse.readoutNEP((det.psatFact-1.)*cumPower, det.boloR, det.nei)
        else:
            if cumPower >= det.psat: return 0.
            else:                    return self.__nse.readoutNEP((det.psat-cumPower),       det.boloR, det.nei)
    
    def sensitivity(self, ch, tp, corr=None):
        if corr is None: corr = self.__corr

        ApEff             = ch.apEff
        PoptArr           = np.array([[self.Popt(   ch.elem[i][j], ch.emiss[i][j], ch.effic[i][j], ch.temp[i][j], ch.freqs)     for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        if corr: NEPPhArr = np.array([[self.NEPph(  ch.elem[i][j], ch.emiss[i][j], ch.effic[i][j], ch.temp[i][j], ch.freqs, ch) for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        else:    NEPPhArr = np.array([[self.NEPph(  ch.elem[i][j], ch.emiss[i][j], ch.effic[i][j], ch.temp[i][j], ch.freqs)     for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        NEPboloArr        = np.array([[self.NEPbolo(PoptArr[i][j],                                ch.detArray.detectors[j])     for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        NEPrdArr          = np.array([[self.NEPrd(  PoptArr[i][j],                                ch.detArray.detectors[j])     for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        
        NEPPhArr, NEPPhArrArr = np.split(NEPPhArr, 2, axis=2)
        NEPPhArr    = np.reshape(NEPPhArr,    np.shape(NEPPhArr)[   :2])
        NEPPhArrArr = np.reshape(NEPPhArrArr, np.shape(NEPPhArrArr)[:2])

        #if 'NA' in NEPrdArr: NEPrdArr = np.array([[np.sqrt(0.21)*np.sqrt(NEPPhArr[i][j]**2    + NEPboloArr[i][j]**2) for j in range(len(NEPrdArr[i]))] for i in range(len(NEPrdArr))])
        #if 'NA' in NEPrdArr: NEPrdArr = np.array([[0.0 for j in range(len(NEPrdArr[i]))] for i in range(len(NEPrdArr))])
        if 'NA' in NEPrdArr: NEPrdArr = np.array([[np.sqrt((1. + ch.detArray.detectors[j].readN)**2 - 1.)*np.sqrt(NEPPhArr[i][j]**2 + NEPboloArr[i][j]**2) for j in range(ch.detArray.nDet)] for i in range(ch.nobs)])
        NEP        = np.sqrt(NEPPhArr**2    + NEPboloArr**2 + NEPrdArr**2)
        NEParr     = np.sqrt(NEPPhArrArr**2 + NEPboloArr**2 + NEPrdArr**2)
        NET        = np.array([[self.__nse.NETfromNEP(NEP[i][j],    ch.freqs, np.prod(ch.effic[i][j], axis=0)) for j in range(ch.detArray.nDet)] for i in range(ch.nobs)]).flatten()*tp.netMgn
        NETar      = np.array([[self.__nse.NETfromNEP(NEParr[i][j], ch.freqs, np.prod(ch.effic[i][j], axis=0)) for j in range(ch.detArray.nDet)] for i in range(ch.nobs)]).flatten()*tp.netMgn
        NETarr     = self.__ph.invVar(NETar)*np.sqrt(float(ch.nobs))*np.sqrt(float(ch.clcDet)/float(ch.detYield*ch.numDet))
        NETarrStd  = np.std(NET)*np.sqrt(1./ch.numDet)
        MS         = 1./np.power(NETarr,    2.)
        MSStd      = abs(1./np.power(NETarr+NETarrStd, 2.) - 1./np.power(NETarr-NETarrStd, 2.))/2.
        
        Sens       = self.__nse.sensitivity(NETarr,    tp.fsky, tp.tobs*tp.obsEff)
        SensStd    = self.__nse.sensitivity(NETarrStd, tp.fsky, tp.tobs*tp.obsEff)

        means = [ch.apEff,
                 np.mean(PoptArr.flatten()),
                 np.mean(NEPPhArr.flatten()),  
                 np.mean(NEPboloArr.flatten()),
                 np.mean(NEPrdArr.flatten()),  
                 np.mean(NEP.flatten()),        
                 np.mean(NET),                 
                 NETarr,              
                 MS,
                 Sens]        
        stds  = [0.,
                 np.std(PoptArr.flatten()),
                 np.std(NEPPhArr.flatten()),    
                 np.std(NEPboloArr.flatten()),  
                 np.std(NEPrdArr.flatten()),   
                 np.std(NEP.flatten()),     
                 np.std(NET),          
                 NETarrStd,
                 MSStd,
                 SensStd]                            

        return means, stds

    def opticalPower(self, ch, tp):
        powSkySide = []
        powDetSide = []
        effDetSide = []
        for i in range(len(ch.elem)):
            powSkySide1 = []
            powDetSide1 = []
            effDetSide1 = []
            for j in range(len(ch.elem[i])):
                powers      = []
                powSkySide2 = []
                powDetSide2 = []
                effSkySide2 = []
                effDetSide2 = []
                #Store efficiency towards sky and towards detector
                for k in range(len(ch.elem[i][j])):
                    effArr = np.vstack([ch.effic[i][j], np.array([1. for f in ch.freqs])])
                    cumEffDet = reduce(lambda x, y: x*y, effArr[k+1:])
                    effDetSide2.append(cumEffDet)
                    if   k == 0: cumEffSky = [[0. for f in ch.freqs]]                         #Nothing sky-side
                    elif k == 1: cumEffSky = [[1. for f in ch.freqs], [0. for f in ch.freqs]] #Only one element sky-side
                    else:        cumEffSky = [reduce(lambda x, y: x*y, effArr[m+1:k]) if m < k-2 else effArr[m+1] for m in range(k-1)] + [[1. for f in ch.freqs], [0. for f in ch.freqs]]
                    effSkySide2.append(np.array(cumEffSky))
                    pow = self.__ph.bbPowSpec(ch.freqs, ch.temp[i][j][k], ch.emiss[i][j][k])
                    powers.append(pow)
                #Store power from sky and power on detector
                for k in range(len(ch.elem[i][j])):
                    powOut = np.trapz(powers[k]*effDetSide2[k]*ch.bandMask, ch.freqs)
                    effDetSide2[k] = np.trapz(effDetSide2[k]*ch.bandMask, ch.freqs)/ch.bandDeltaF
                    powDetSide2.append(powOut)
                    powIn = sum([np.trapz(powers[m]*effSkySide2[k][m]*ch.bandMask, ch.freqs) for m in range(k+1)])
                    powSkySide2.append(powIn)
                powSkySide1.append(powSkySide2)
                powDetSide1.append(powDetSide2)
                effDetSide1.append(effDetSide2)
            powSkySide.append(powSkySide1)
            powDetSide.append(powDetSide1)
            effDetSide.append(effDetSide1)
        #Build table of optical powers and efficiencies for each element
        shape = np.shape(powSkySide)
        newshape = (shape[0]*shape[1], shape[2])
        powSkySide = np.transpose(np.reshape(powSkySide, newshape))
        powDetSide = np.transpose(np.reshape(powDetSide, newshape))
        effDetSide = np.transpose(np.reshape(effDetSide, newshape))
        means = [np.mean(powSkySide, axis=1),
                 np.mean(powDetSide, axis=1),
                 np.mean(effDetSide, axis=1)]
        stds  = [np.std(powSkySide,  axis=1),
                 np.std(powDetSide,  axis=1),
                 np.std(effDetSide,  axis=1)]
        #print means
        return means, stds

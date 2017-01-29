#!/usr/local/bin/python

#Classes for handling common calculations
#class Calculation

#python Version 2.7.2
import numpy as np
import physics as phy
import experiment as exp
import noise as nse

#Class for common calculations
#calcPopt(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, nModes=None)
#calcETF(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psat=None, nModes=None)
#calcPhotonNEP(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, bf=None, nModes=None)
#calcMappingSpeed(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psatFact=None, Tb=None, Tc=None, n=None, nDet=None, nei=None, boloR=None, bf=None, nModes=None)
#calcMappingSpeed_fixedPsat(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psat=None, Tb=None, Tc=None, n=None, nDet=None, nei=None, boloR=None, bf=None, nModes=None)
#makeSensTable(self, exp=None, outFile=None, fixedPsat=False)
class Calculation:
    def __init__(self):
        #***** Private variables *****
        self.__ph  = phy.Physics()
        self.__pb2 = exp.PB2()
        self.__nse = nse.Noise()

        #Unit conversions
        self.__GHz    = 1.e-09
        self.__mm     = 1.e+03
        self.__pct    = 1.e+02
        self.__pW     = 1.e+12
        self.__aWrtHz = 1.e+18
        self.__uK     = 1.e+06
        self.__uK2    = 1.e-12

        #Directory for writing tables
        self.__dir = './TXT/'

    #***** Public methods *****
    #Calculate total in-band optical power [W]
    def calcPopt(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, nModes=None):
        if bandCenter == None:
            bandCenter = self.__pb2.dBandCenter
        if fbw == None:
            fbw = self.__pb2.dFbw
        if nModes == None:
            nModes = self.__pb2.nModes

        #Need an extra efficiency for the calculation
        effArr = np.insert(effArr, len(effArr), 1.0)

        #Photon powers
        cumPower = 0 #Total power
        skyPower = 0 #Power from the sky
        rvrPower = 0 #Power from the receiver
        hwpPower = 0 #Power from the HWP
        
        #Efficiencies
        totEff = 0 #End-to-end efficiency
        rvrEff = 0 #Receiver efficiency
        hwpEff = 0 #Efficiency of everything detector-side of the HWP
        
        #Run the calculation
        for j in range(len(elemArr)):
            #Element
            elem = str(elemArr[j])
            #Element emissivity
            elemEmm = float(emmArr[j])
            #Element temperature
            elemTemp = float(tempArr[j])
            #Efficiency of everything detector-side of the element
            cumEff = reduce(lambda x, y: float(x)*float(y), effArr[j+1:])
            if j == 0:
                totEff = cumEff
            if j == 1:
                rvrEff = cumEff
            if 'HWP' in elem:
                hwpEff = cumEff
            #Add power seen at detector from that element
            pow = self.__ph.bbPower(elemEmm*cumEff, bandCenter, fbw, elemTemp, nModes)
            cumPower += pow
            if j < 2:
                skyPower += pow
            else:
                rvrPower += pow
            if 'HWP' in elem:
                hwpPower = pow

        return cumPower, skyPower, rvrPower, hwpPower, totEff, rvrEff, hwpEff

    #Calculate Psat/Popt
    def calcETF(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psat=None, nModes=None):
        if bandCenter == None:
            bandCenter = self.__pb2.dBandCenter
        if fbw == None:
            fbw = self.__pb2.dFbw
        if psat == None:
            psat = self.__pb2.dBandPsat
        if nModes == None:
            nModes = self.__pb2.nModes

        #Need an extra efficiency for the calculation
        effArr.insert(len(effArr), 1.0)
        
        #Calculate cumulative photon power with the HWP
        cumPower = self.calcPopt(elemArr, emmArr, effArr, tempArr, bandCenter, fbw, nModes)[0]
            
        #Return cumulative photon power from all optical elements
        return psat/cumPower

    #Calculate photon NEP
    def calcPhotonNEP(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, bf=None, nModes=None):
        if bandCenter == None:
            bandCenter = self.__pb2.dBandCenter
        if fbw == None:
            fbw = self.__pb2.dFbw
        if bf == None:
            bf = self.__pb2.bf
        if nModes == None:
            nModes = self.__pb2.nModes
        
        #Need an extra efficiency for the calculation
        effArr = np.insert(effArr, len(effArr), 1.0)

        #Calculate cumulative photon power
        cumPowerIntegrands = []
        cumPower = 0
        for j in range(len(elemArr)):
            #Element emissivity
            elemEmm = float(emmArr[j])
            #Element temperature
            elemTemp = float(tempArr[j])
            #Efficiency of everything detector-side of the element
            cumEff = reduce(lambda x, y: float(x)*float(y), effArr[j+1:])
            #Add power seen at detector from that element
            cumPower += self.__ph.bbPower(elemEmm*cumEff, bandCenter, fbw, elemTemp, nModes)
            #Add cumulative power integrand to array for each element
            cumPowerIntegrands.append(lambda f, elemEmm=elemEmm, cumEff=cumEff, elemTemp=elemTemp, nModes=nModes: self.__ph.bbPowSpec(elemEmm*cumEff, f, elemTemp, nModes))
        #Photon NEP
        NEP_ph    = self.__nse.photonNEP(cumPowerIntegrands, bandCenter, fbw)
        
        #Return optical power and photon noise
        return cumPower, NEP_ph

    #Calculate mapping speed [(K^2-sec)^-1]
    def calcMappingSpeed(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psatFact=None, Tb=None, Tc=None, n=None, nDet=None, detYield=None, nei=None, boloR=None, bf=None, nModes=None):
        if bandCenter == None:
            bandCenter = self.__pb2.dBandCenter
        if fbw == None:
            fbw = self.__pb2.dFbw
        if psatFact == None:
            psatFact = self.__pb2.psatFact
        if Tb == None:
            Tb = self.__pb2.Tb
        if Tc == None:
            Tc = self.__pb2.Tc
        if n == None:
            n = self.__pb2.n
        if nDet == None:
            nDet = self.__pb2.nDetArr[1]
        if detYield == None:
            detYield = 1.0
        if nei == None:
            nei = self.__pb2.nei
        if boloR == None:
            boloR = self.__pb2.boloR
        if bf == None:
            bf = self.__pb2.bf
        if nModes == None:
            nModes = self.__pb2.nModes

        #Need an extra efficiency for the calculation
        effArr = np.insert(effArr, len(effArr), 1.0)
        #Efficiency of full optical path
        skyEff = reduce(lambda x, y: float(x)*float(y), effArr) 

        #Photon NEP/NET and optical power
        cumPower, NEP_ph = self.calcPhotonNEP(elemArr, emmArr, effArr, tempArr, bandCenter, fbw, bf, nModes)
        NET_ph = self.__nse.NETfromNEP(NEP_ph, bandCenter, fbw, skyEff)
        #Bolometer NEP/NET
        NEP_bolo = self.__nse.bolometerNEP(psatFact*cumPower, n, Tc, Tb)
        NET_bolo = self.__nse.NETfromNEP(NEP_bolo, bandCenter, fbw, skyEff)
        #Readout NEP/NET
        NEP_rd = self.__nse.readoutNEP((psatFact - 1.0)*cumPower, boloR, nei)
        NET_rd = self.__nse.NETfromNEP(NEP_rd, bandCenter, fbw, skyEff)
        #Total NEP/NET
        NEP = np.sqrt(NEP_ph**2 + NEP_bolo**2 + NEP_rd**2)
        NET = self.__nse.NETfromNEP(NEP, bandCenter, fbw, skyEff)
        #NET array
        NETarr = self.__nse.NETarr(NET, nDet, detYield)
        #Mapping speed
        MS = self.__nse.mappingSpeed(NET, nDet, detYield)

        return cumPower, NEP_ph, NEP_bolo, NEP_rd, NEP, NET_ph, NET_bolo, NET_rd, NET, NETarr, MS
    
    #Calculate mapping speed [(K^2-sec)^-1]
    def calcMappingSpeed_fixedPsat(self, elemArr, emmArr, effArr, tempArr, bandCenter=None, fbw=None, psat=None, Tb=None, Tc=None, n=None, nDet=None, detYield=None, nei=None, boloR=None, bf=None, nModes=None):
        if bandCenter == None:
            bandCenter = self.__pb2.dBandCenter
        if fbw == None:
            fbw = self.__pb2.dFbw
        if psat == None:
            psat = self.__pb2.dBandPsat
        if Tb == None:
            Tb = self.__pb2.Tb
        if Tc == None:
            Tc = self.__pb2.Tc
        if n == None:
            n = self.__pb2.n
        if nDet == None:
            nDet = self.__pb2.d_nDet
        if detYield == None:
            detYield = 1.0
        if nei == None:
            nei = self.__pb2.nei
        if boloR == None:
            boloR = self.__pb2.boloR
        if bf == None:
            bf = self.__pb2.bf
        if nModes == None:
            nModes = self.__pb2.nModes

        #Need an extra efficiency for the calculation
        effArr = np.insert(effArr, len(effArr), 1.0)
        #Efficiency of full optical path
        skyEff = reduce(lambda x, y: float(x)*float(y), effArr) 

        #Photon NEP/NET and optical power
        cumPower, NEP_ph = self.calcPhotonNEP(elemArr, emmArr, effArr, tempArr, bandCenter, fbw, bf, nModes)
        NET_ph = self.__nse.NETfromNEP(NEP_ph, bandCenter, fbw, skyEff)
        #Bolometer NEP/NET
        NEP_bolo = self.__nse.bolometerNEP(psat, n, Tc, Tb)
        NET_bolo = self.__nse.NETfromNEP(NEP_bolo, bandCenter, fbw, skyEff)
        #Readout NEP/NET
        NEP_rd = self.__nse.readoutNEP((psatFact - 1.0)*cumPower, boloR, nei)
        NET_rd = self.__nse.NETfromNEP(NEP_rd, bandCenter, fbw, skyEff)
        #Total NEP/NET
        NEP = np.sqrt(NEP_ph**2 + NEP_bolo**2 + NEP_rd**2)
        NET = self.__nse.NETfromNEP(NEP, bandCenter, fbw, skyEff)
        #NET array
        NETarr = self.__nse.NETarr(NET, nDet, detYield)
        #Mapping speed
        MS = self.__nse.mappingSpeed(NET, nDet, detYield)

        return cumPower, NEP_ph, NEP_bolo, NEP_rd, NEP, NET_ph, NET_bolo, NET_rd, NET, NETarr, MS
        
    #Create a sensitivity table
    def makeSensTable(self, exp=None, outFile=None, fixedPsat=False):
        if exp == None:
            exp = self.__pb2
        if outFile == None:
            outFile = "%s%s_SensitivityTable.txt" % (self.__dir, exp.name)
        
        #Open file to which we will write the calculated parameters for this scenario
        f = open(outFile, "w")
        #Write the column titles
        f.write("%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s\n"
                % ("Freq", "FBW", "PixSz", "NumDet", "ApertEff", "EdgeTap", "Popt", "NEPph", "NEPbolo", "NEPread", "NEPdet", "NETdet", "NETarr", "Mapping Speed"))
        #Write the units for each column
        f.write("%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s%-11s\n" 
                % ("[GHz]", "", "[mm]", "", "[%]", "[dB]", "[pW]", "[aW/rtHz]", "[aW/rtHz]", "[aW/rtHz]", "[aW/rtHz]", "[uK-rtSec]", "[uK-rtSec]", "[(uK^2 s)^-1]"))

        #Gather relevant experimental parameters
        psatFact   = exp.psatFact
        Tb         = exp.Tb
        Tc         = exp.Tc
        n          = exp.n
        nei        = exp.nei
        boloR      = exp.boloR
        bf         = exp.bf
        nModes     = exp.nModes
        detYield   = exp.detYield
        
        #Store the Overall Sensitivity and detector count values for writing to the table
        SensitivityInvSqTotal = 0.
        DetectorCountTotal = 0.
        NETArrayInvSqTotal = 0.
        noise = []

        #Calculate loading, optical NEP, bolo NEP, readout NEP,
        #detector NEP, detector NET, and NET array for LFT
        for i in range(exp.numBands):
            #Identify the band center and fbw for this interation
            bandID     = i
            bandCenter = exp.bandCenterArr[i]
            fbw        = exp.fbwArr[i]
            pixSize    = exp.pixSizeArr[i]
            numDet     = exp.nDetArr[i]
            numPix     = exp.nPixArr[i]
            
            #Tally the total detector count
            DetectorCountTotal += numDet
            
            #Retrieve the optical elements
            elemArr, emisArr, effArr, tempArr = exp.getOpticalParams(bandID)
            
            #Calculate sensitivity
            if fixedPsat:
                cumPower, NEPphoton, NEPbolo, NEPread, NEPTotal, NETphoton, NETbolo, NETread, NET, NETArray, MS = self.calcMappingSpeed_fixedPsat(elemArr, emisArr, effArr, tempArr, bandCenter, fbw, psatFact, Tb, Tc, n, numDet, detYield, nei, boloR, bf, nModes)
            else:
                cumPower, NEPphoton, NEPbolo, NEPread, NEPTotal, NETphoton, NETbolo, NETread, NET, NETArray, MS = self.calcMappingSpeed(elemArr, emisArr, effArr, tempArr, bandCenter, fbw, psatFact, Tb, Tc, n, numDet, detYield, nei, boloR, bf, nModes)
            
            #Calculate aperture efficiency
            ApertEff = effArr[elemArr.tolist().index('LyotStop')]
            
            #Write the values to the table
            f.write("%-11.1f%-11.2f%-11.1f%-11.0f%-11.2f%-11.2f%-11.2f%-11.2f%-11.2f%-11.2f%-11.2f%-11.2f%-11.2f%-11.4f\n" 
                    % (bandCenter*self.__GHz, fbw, pixSize*self.__mm, numDet, ApertEff*self.__pct, 10.*np.log10(1. - ApertEff), cumPower*self.__pW, 
                       NEPphoton*self.__aWrtHz, NEPbolo*self.__aWrtHz, NEPread*self.__aWrtHz, NEPTotal*self.__aWrtHz, NET*self.__uK, NETArray*self.__uK, MS*self.__uK2))

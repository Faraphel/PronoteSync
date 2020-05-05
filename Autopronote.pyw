import time
import os
import pickle
import platform
import subprocess
import sys
import traceback
from threading import Thread
from PIL import Image

EnableVirtualDisplay = False # Permet de prendre des captures d'écrans.

if platform.system() != "Windows" and EnableVirtualDisplay: # Sur linux, crée un faux écran pour les captures d'écrans et contourné des bugs
    from pyvirtualdisplay import Display
    VirtualDisplay = Display(visible = 0, size = (1980, 1080))
    VirtualDisplay.start()

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

import tweepy

#############################################

DefaultWaitingTime = 10 # Temps entre chaque boucle au minimum
Timeout = 60 # Timeout, incrémenté toute les secondes et remis a zéro à chaque page
CrashRaw = 0 # Si ce nombre est trop incrémenté, le programme se relance depuis le début sur linux.
SilentMode = False # Rend invisible le programme ( hors débug )
CrashLog = False # Va enregistrer dans un fichier local des informations sur le processeur, la ram et la température a chaque fin de loop.
Tweet_Enabled = True # Désactive les tweets.
ScreenShot_Enabled = False # Si non, désactive la fonction de capture d'écran (Car pour l'instant inutilisable) [peut diminuer considérablement le temps d'un cycle]
User = "xxxxxxxxxxxxxxx"
Password = "xxxxxxxxxx"

ACCESS_TOKEN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
ACCESS_TOKEN_SECRET = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
API_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
API_KEY_SECRET = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

#############################################
#############################################
try:
    TweetAuth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET) # S'authentifie à L'API de tweeter
    TweetAuth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET) # S'authentifie au compte @PronoteSync
    TweetAPI = tweepy.API(TweetAuth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True) # Configure l'API et son objet

    print("Tweeter authentifié.")
except Exception as e:
    print("Tweeter non accessible.")

#############################################
#############################################

def SaveError(Error):
    with open("Error.log", "a") as File:
        File.write(Error)


def InitWebDriver():
    global driver

    try:
        options = webdriver.ChromeOptions()
        if SilentMode and platform.system() == "Windows": options.headless = True
        options.add_argument('--no-sandbox') # Conseiller par les forums
        options.add_argument('--window-size=1980,1080') # Taille de l'écran

        Chromedriver_Path = "chromedriver"
        if platform.system() != "Windows": Chromedriver_Path = "/usr/lib/chromium-browser/chromedriver"

        driver = webdriver.Chrome(Chromedriver_Path, options=options)
        driver.get("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") # Url du site de pronote

    except Exception as e:
        print("Impossible de créer l'interface web. (%s)\n\n" % traceback.format_exc())
        driver.quit()
        sys.exit()

    else: print("Chargement de l'interface web réussi.")

def ReInitWebDriver():
    global driver
    driver.quit()
    InitWebDriver()

InitWebDriver()

############## PAGE DE CONNECTION -> MP ##############

def Connexion():
    while True:
        try:
            driver.implicitly_wait(Timeout)

            WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.ID, "email")))
            Entry = driver.find_element_by_id("email")
            Entry.send_keys(User) # Identifiant

            WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.ID, "password")))
            Entry = driver.find_element_by_id("password")
            Entry.send_keys(Password) # Mot de passe

            Entry.send_keys("\n") # Entrer

        except Exception as e:
            print("Impossible de se connecter à pronote. (%s)\n\n" % traceback.format_exc())
            driver.refresh()

        else:
            print("Connection réussi.")
            break

Connexion()
############## PAGE DE CONNECTION -> MP ##############

LoopCounter = 0


class CrashCheck(Thread):
        def __init__(self):
                Thread.__init__(self)

        def run(self):
                global LoopCounter
                sys.stdout.write("Démarrage de l'auto testeur de crash.\n")

                while True:
                    StartLoop = LoopCounter
                    time.sleep(5 * 60)
                    if StartLoop == LoopCounter:
                        print("Auto Crash : L'application n'a pas répondu depuis 5 minutes.")
                        if platform.system() != "Windows": VirtualDisplay.sendstop()
                        driver.quit()
                        sys.exit()


class SelfReboot(Thread):
        def __init__(self):
                Thread.__init__(self)

        def run(self):
                if platform.system() != "Windows":
                        sys.stdout.write("Démarrage du self-reboot.\n")
                        time.sleep(60) # Pour éviter que le programme redémmarage plusieurs fois de suite

                        while True:
                                time.sleep(45)
                                Time = time.strftime("%H:%M")
                                if Time == "20:00" or Time == "08:00":
                                        os.system("reboot")

CrashCheckThread = CrashCheck()
CrashCheckThread.setDaemon(True)
CrashCheckThread.start()

SelfRebootThread = SelfReboot()
SelfRebootThread.setDaemon(True)
SelfRebootThread.start()


def AnalyseEDT(WeekNumber):

    try:
        WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.CLASS_NAME, "EmploiDuTemps_Element")))
        EDTElement = driver.find_element_by_class_name("EmploiDuTemps_Element")
        EDTElement_Prefix = "_".join(EDTElement.get_attribute("id").split("_")[0:3])
    except Exception: # Les préfixes n'ont pas pu être trouver, s'est donc qu'il n'y a pas de cours dans la semaine.
        return


    i = 0
    while True:
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "%s_%i" % (EDTElement_Prefix, i)))) # Attend aux maximum 5 secondes l'affichage des cours
            Cours = driver.find_element_by_id("%s_%i" % (EDTElement_Prefix, i)) # Cherche dans tout les cours notés

            Cours.click() # Affiche les informations supplémentaire, permet d'avoir l'horaire
            WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.CLASS_NAME, "EnteteCoursLibelle"))) # Attend l'affichage de l'horaire


            try:
                CoursStatut = driver.find_element_by_class_name("EnteteCoursStatut") # Statut du cours
            except NoSuchElementException:
                class CoursStatut:
                    text = None

            CoursDate = driver.find_element_by_class_name("EnteteCoursLibelle") # Capture l'horaire
            DateFormat = CoursDate.text.split(" ") # Reformatage de la date

            CoursName = driver.find_element_by_xpath("//div[@class='TextePastille ie-ellipsis']")


            CoursData = {"Statut": CoursStatut.text,
                "Info": CoursName.text,
                "Duration": DateFormat[0],
                "DayName": DateFormat[2],
                "Day": DateFormat[3],
                "Schedule": DateFormat[5],
                "Media": None}


            if ["Remplacement", "Prof. absent", "Cours maintenu", "Cours annulé", "Cours modifié", "Changement de salle"].count(CoursData["Statut"]): # Liste de tout les statuts
                EditedCours.append(CoursData) # Si le cours à un statut, il est noté dans cette liste

                CoursFiche = driver.find_element_by_class_name("ConteneurFiches")

                Screenshot_Path = "Temp.png"

                try:
                    Hint = driver.find_element_by_class_name("SansOutline")
                    driver.execute_script("""
                    var element = arguments[0];
                    element.parentNode.removeChild(element);
                    """, Hint) # Sert à supprimer les bulles d'informations qui apparaissent et gache les captures d'écran sur un écran trop petit.
                except: pass

                driver.save_screenshot(Screenshot_Path)

                x, y = CoursFiche.location.values()
                h, w = CoursFiche.size.values()

                Screenshot_Image = Image.open(Screenshot_Path)
                Screenshot_Image = Screenshot_Image.crop((x, y, w + x, h + y))
                Screenshot_Image.save(Screenshot_Path)

                CoursData["Media"] = TweetAPI.media_upload(Screenshot_Path)


            if not list(GCD_Sort.keys()).count(DateFormat[2]): GCD_Sort[DateFormat[2]] = {} # DateFormat[2] est le nom du jour
            GCD_Sort[DateFormat[2]][DateFormat[5]] = CoursData # DateFormat[5] est l'heure


            if not(SilentMode):
                print("\n" + str(CoursData)) # LOG
                #print("%s_%i" % (EDTElement_Prefix, i))

        except TimeoutException as e: # Plante si tous les cours ont été noté
            if not(SilentMode): print("\nAucun autre cours détecté")
            break

        except ElementNotVisibleException: pass # Arrive quand des cours sont déplacés, certains sont invisible
        except ElementNotInteractableException: pass # Ces éléments buggé ne sont pas interractible.
        except StaleElementReferenceException: pass # Semble être une autre erreur fréquente.
        except ElementClickInterceptedException: pass # Semble arriver quand un clic est intercepté par la page

        except Exception as e:
            print("Une erreur c'est produite dans la recherche de prof. absent. (%s)\n\n" % traceback.format_exc())

        finally:
            i += 1


while True: # Fait une boucle de recherche de modifications
	##############################################
        try:
                LoopCounter += 1
                TimeStartLoop = time.time()
                Time = time.strftime("%H_%M_%S %b %d %Y")
                Date = time.strftime("%b %d %Y")

                _Stop = False

                if not os.path.exists(Date): os.makedirs(Date)
	############## MENU PRINCIPAL -> EDT ##############
                try:
                    WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.CLASS_NAME, "objetAffichagePageAccueil_wrapper"))) # Chargement du boutton
                    PronoteBanner = driver.find_element_by_class_name("ObjetBandeauEspace")

                    driver.execute_script("GInterface.Instances[1]._surToutVoir(12)")

                except:
                    try:
                        driver.find_element_by_xpath("//*[contains(text(), 'Connexion impossible')]") # Page qui s'affiche s'il pronote est down
                        print("Attente : Pronote est actuellement indisponible.")

                    except Exception as e:
                        print("\nErreur lors de la reconnection (%s)\n\n" % traceback.format_exc())

                        ReInitWebDriver()
                        Connexion()

                    finally:
                        driver.refresh()
                        _Stop = True


                if _Stop: continue
		###################################################
		############## MENU PRINCIPAL -> EDT ##############
		###################################################

                WebDriverWait(driver, Timeout).until(EC.presence_of_element_located((By.ID, "GInterface.Instances[1].Instances[1].Instances[0]_Zone_Grille")))

                driver.implicitly_wait(0.5)
                GCD_Sort = {}
                EditedCours = []

                ActualWeekButton = driver.find_element_by_class_name("Calendrier_Jour_Selection") # Récupère la semaine actuel
                WeekButtonID, ActualWeek = "_".join(ActualWeekButton.get_attribute("id").split("_")[0:-1]), int("_".join(ActualWeekButton.get_attribute("id").split("_")[-1]))

                AnalyseEDT(ActualWeek) # Analyse la semaine actuel

                NextWeekButton = driver.find_element_by_id("%s_%i" % (WeekButtonID, ActualWeek + 1))
                NextWeekButton.click() # Se rend à la semaine suivante

                AnalyseEDT(ActualWeek + 1) # Analyse la semaine prochaine

		############## DETECTION DE NOUVEAUTER ##############

                AlreadyNotified = []
                KnownEditedCours = []

		##############

                try:
                    with open("EditedCours.pickle", "rb") as File: KnownEditedCours = pickle.load(File)
                except Exception as e: KnownEditedCours = []

                for Cours in EditedCours: # Cherche parmis tous les cours avec un statut
                    _Stop = False # Change si le cours à déjà été scanner antérieurement
                    for KnownCours in KnownEditedCours: # Cherche parmis ceux déjà scanner
                        if (KnownCours["Day"] == Cours["Day"]) and (KnownCours["Schedule"] == Cours["Schedule"]): _Stop = True # Si déjà scanné, alors n'est pas notifié

                    if not _Stop:
                        print("\n%s est un nouveau cours modifié ! " % str(Cours))
                        print("Le cours \"%s\" du %s %s à %s durant %s est modifié pour \"%s\"" % (Cours["Info"].replace("\n", " | "), Cours["DayName"], Cours["Day"], Cours["Schedule"], Cours["Duration"], Cours["Statut"]))

                        if Tweet_Enabled:
                        	TweetAPI.update_status(status = "Le cours \"%s\" du %s %s à %s durant %s est modifié pour \"%s\"" % (Cours["Info"].replace("\n", " | "), Cours["DayName"], Cours["Day"], Cours["Schedule"], Cours["Duration"], Cours["Statut"]),
                                                       media_ids = [Cours["Media"].media_id]) # Tweet les nouveautés

                        AlreadyNotified.append(Cours)

                        KnownEditedCours.append(Cours)

		##############

                with open("EditedCours.pickle", "wb") as File: pickle.dump(KnownEditedCours, File) # Ajoute les cours détecter à la base de donné
                if not(SilentMode): print(KnownEditedCours)


                CrashRaw = 0
                print("\nBoucle %i - Réussi" % LoopCounter)
                ExecutionTime = time.time() - TimeStartLoop
                WaitingTime = DefaultWaitingTime - ExecutionTime # Calcul le temps de la synchronisation pour l'ajuster au temps voulu
                print("Temps d'éxecution - %i" % ExecutionTime)

                if CrashLog and platform.system() != "Windows":
                    with open("CrashLog.txt", "a") as Log:
                        Log.write(time.ctime() + "\n")
                        Log.write("TEMP : " + str(subprocess.check_output("vcgencmd measure_temp", shell=True))  + "\n")
                        Log.write("RAM  : " + str(subprocess.check_output("vcgencmd get_mem reloc", shell=True)) + "\n")
                        Log.write("\n")

                if WaitingTime >= 0: time.sleep(WaitingTime) # S'arrete pendant moins de 3 minutes avant de relancer les recherches de modifications
                driver.refresh()

        except Exception as e:
                CrashRaw += 1
                Error = traceback.format_exc()

                SaveError(Error)
                print("\nBoucle %i - Echec (%s)\n\n" % (LoopCounter, Error))

                time.sleep(10)
                driver.refresh()

                if CrashRaw >= 3:
                    CrashRaw = 0
                    print("Trop d'erreur se sont enchaînées, réinitialisation de l'interface web.\n\n\n")
                    ReInitWebDriver()

if platform.system() != "Windows": VirtualDisplay.sendstop()
driver.quit()
sys.exit()

# Copyright Raphaël

'''
Tests to ensure that a QGIS installation contains Processing dependencies
and they are correctly configured by default
'''

import os
import sys
import unittest

from qgis.utils import plugins, iface
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsRasterLayer, QgsProject

from coretests.tests.packages_tests import PackageTests
from coretests.tests.platform_tests import TestImports, TestSupportedFormats, TestOtherCommandLineUtilities

from qgis.PyQt.QtNetwork import QSslCertificate

testPath = os.path.dirname(__file__)

TEST_URLS = "TEST_URLS"

def _loadSpatialite():
    uri = QgsDataSourceUri()
    uri.setDatabase(os.path.join(os.path.dirname(__file__), "data", "elk.sqlite"))
    schema = ''
    table = 'elk'
    geom_column = 'the_geom'
    uri.setDataSource(schema, table, geom_column)
    layer = QgsVectorLayer(uri.uri(), "test", 'spatialite')
    assert layer.isValid()
    QgsProject.instance().addMapLayer(layer)

def _loadTestLayer():
    pass

def _openDBManager():
    plugins["db_manager"].run()

def _openLogMessagesDialog():
    widgets = [el for el in iface.mainWindow().children() if el.objectName() == "MessageLog"]
    widgets[0].setVisible(True)

def _openAboutDialog():
    iface.actionAbout().trigger()

def _loadArcMap():
    uri = "layer='2' url='https://sampleserver6.arcgisonline.com/arcgis/rest/services/USA/MapServer'"
    layer = QgsRasterLayer(uri, 'testlayer', 'arcgismapserver')
    assert layer.isValid()

def _loadArcFeature():
    uri = "url='https://sampleserver6.arcgisonline.com/arcgis/rest/services/USA/MapServer/2'"
    layer = QgsVectorLayer(uri, 'testlayer', 'arcgisfeatureserver')
    assert layer.isValid()

def _loadWcs():
    valid = {}
    urls = os.getenv(TEST_URLS).split(",")
    for url in urls:
        try:
            url = url.strip() + "/wcs"
            uri = QgsDataSourceUri()
            uri.setParam('url',url )
            uri.setParam("identifier", "testlayer")
            layer = QgsRasterLayer(str(uri.encodedUri()), 'testlayer', 'wcs')
            valid[url] = layer.isValid()
        except:
            valid[url] = False
    failed = [k for k,v in valid.items() if not v]
    if failed:
        raise AssertionError("Test failed for the following URLs: " + str(failed))

def _modifyAndLoadWfs():
    valid = {}
    urls = os.getenv(TEST_URLS).split(",")
    for url in urls:
        try:
            url = url.strip() + "/wfs"
            uri = "%s?typename=union&version=1.0.0&request=GetFeature&service=WFS" % url
            layer = QgsVectorLayer(uri, "testlayer", "WFS")
            featureCount = layer.featureCount()
            featureid = list(layer.getFeatures())[0].id()
            layer.startEditing()
            layer.deleteFeature(featureid)
            layer.commitChanges()
            layer = QgsVectorLayer(uri, "testlayer", "WFS")
            valid[url] =  layer.featureCount() == featureCount - 1
        except:
            valid[url] = False
    failed = [k for k,v in valid.items() if not v]
    if failed:
        raise AssertionError("Test failed for the following URLs: " + str(failed))

def _loadWfsToBeEdited(name="testlayer"):
    valid = {}
    url = os.getenv(TEST_URLS).split(",")[0] + + "/wfs"        
    url = url.strip() + "/wfs"
    uri = "%s?typename=usa:states&version=1.0.0&request=GetFeature&service=WFS&username=admin&password=geoserver" % url
    layer = QgsVectorLayer(uri, name, "WFS")
    if not layer.isValid():
        raise AssertionError("Test failed loading WFS layer")


AUTHDB_MASTERPWD = "password"

def _initAuthManager():
    authm = QgsAuthManager.instance()
    # check if QgsAuthManager has been already initialised... a side effect
    # of the QgsAuthManager.init() is that AuthDbPath is set
    if authm.masterPasswordIsSet():
        msg = 'Auth master password not set from passed string'
        assert authm.masterPasswordSame(AUTHDB_MASTERPWD), msg
    else:
        msg = 'Master password could not be set'
        assert authm.setMasterPassword(AUTHDB_MASTERPWD, True), msg


def _populatePKITestCerts():
    removePKITestCerts()
    assert (AUTHCFGID is None)
    # set alice PKI data
    pkipath = os.path.join(os.path.dirname(__file__), 'data', 'certs', 'certs-keys')
    p_config = QgsAuthMethodConfig()
    p_config.setName("alice")
    p_config.setMethod('PKI-PKCS#12')
    p_config.setUri("http://example.com")
    p_config.setConfig("certpath", os.path.join(pkipath, 'alice.p12'))
    assert p_config.isValid()
    # add authorities
    cacerts = QSslCertificate.fromPath(os.path.join(pkipath, 'subissuer-issuer-root-ca_issuer-2-root-2-ca_chains.pem'))
    assert cacerts is not None
    authm.storeCertAuthorities(cacerts)
    authm.rebuildCaCertsCache()
    authm.rebuildTrustedCaCertsCache()

    # register alice data in auth
    authm.storeAuthenticationConfig(p_config)
    authid = p_config.id()
    assert (authid is not None)
    assert (authid != '')
    return authid

def _addToDbAndLoadLayer():
    host = "postgis.boundless.test"
    db = "opengeo"
    username: "docker"
    password = "docker"
    port  = "55432"
    layer = _loadTestLayer()

    #No-PKI
    uri = QgsDataSourceURI()
    uri.setConnection(host, port, db, username, password)
    uri.setDataSource("public", "test", "geom", "", "gid")
    error = QgsVectorLayerExporter.exportLayer(layer, uri, "postgres", None, False, False)
    assert error == QgsVectorLayerExporter.NoError

    uri = QgsDataSourceURI()
    uri.setConnection(host, port, db, username, password)
    uri.setDataSource("", "test", "geom", "", "gid")
    layer = QgsVectorLayer(uri.uri(), "testlayer", "postgres")
    assert layers.isValid()

    #PKI
    _initAuthManager()
    authid = _populatePKITestCerts()

    uri = QgsDataSourceURI()
    uri.setConnection(host, port, db, username, password, QgsDataSourceUri.SslRequire, authid)
    uri.setDataSource("public", "test", "geom", "", "gid")
    error = QgsVectorLayerExporter.exportLayer(layer, uri, "postgres", None, False, False)
    assert error == QgsVectorLayerExporter.NoError

    uri = QgsDataSourceURI()
    uri.setConnection(host, port, db, username, password, QgsDataSourceUri.SslRequire, authid)
    uri.setDataSource("", "test", "geom", "", "gid")
    layer = QgsVectorLayer(uri.uri(), "testlayer", "postgres")
    assert layers.isValid()

def functionalTests():
    try:
        from qgistester.test import Test
    except:
        return []

    logTest = Test("Verify in-app message log has no errors for default install. QGIS-62")
    logTest.addStep("Open log messages panel",
                    prestep=lambda:_openLogMessagesDialog())
    logTest.addStep("Review 'General' tab output. Check it has no issues",
                    isVerifyStep=True)
    logTest.addStep("Check there are no errors in 'Plugins' tab",
                    isVerifyStep=True)
    logTest.addStep("If exists, check there are no errors in 'Python warning' tab",
                    isVerifyStep=True)
    logTest.addStep("If exists, check there are no errors in 'Qt' tab",
                    isVerifyStep=True)
    logTest.addStep("Review the Init Script, check there are no errors in 'Qt' tab",
                    isVerifyStep=True)
    logTest.addStep("Review any other existing tabs, check that there are no errors",
                    isVerifyStep=True)

    spatialiteTest = Test("Test Spatialite. QGIS-120")
    spatialiteTest.addStep("Load Spatialite layer",
                           prestep=lambda:_loadSpatialite())
    spatialiteTest.addStep("Open DB Manager",
                           prestep=lambda:_openDBManager())
    spatialiteTest.addStep("Check that 'test' layer is available "
                           "in DB manager, in 'Virtual layers/QGIS layers'",
                           isVerifyStep=True)

    aboutTest = Test("Verify dependency versions and providers in About dialog. QGIS-53")
    aboutTest.addStep("Open About dialog",
                      prestep=lambda:_openAboutDialog())
    if sys.platform == 'darwin':
        filePath = os.path.join(testPath, "data", "about.mac")
    else:
        filePath = os.path.join(testPath, "data", "about.windows")
    with open(filePath) as f:
        content = f.readlines()
    data = ""
    for line in content:
        data += "<p>{}</p>".format(line)
    aboutTest.addStep("Verify that content of the About dialog matches"
                      "following data\n{}\n\n".format(data),
                      isVerifyStep=True)

    arcmapTest = Test("Test ArcMapserver")
    arcmapTest.addStep("Load layer",
                           prestep=_loadArcMap)

    arcfeatureTest = Test("Test ArcFeatureserver")
    arcfeatureTest.addStep("Load layer",
                           prestep=_loadArcFeature)

    wcsTest = Test("Test WCS")
    wcsTest.addStep("Load WCS layer",
                           prestep=_loadWcs)

    wfsTest = Test("Test WFS")
    wfsTest.addStep("Modify and load WFS layer",
                           prestep=_modifyAndLoadWfs)

    postgisTest = Test("Test PostGIS")
    postgisTest.addStep("Create and load PostGIS layer",
                           prestep=_addToDbAndLoadLayer)

    offlineTest = Test("WFS Smoke Test (Server) - Offline Editing")
    offlineTest.addStep("Load WFS layer layer",
                           prestep=_loadWfsToBeEdited)
    offlineTest.addStep("Enable *Offline editing* plugin from *Plugins > Manage and install plugins* in the *Installed* tab.",
                           isVerifyStep=True)
    offlineTest.addStep("Convert the project to an offline project by selecting *Database > Offline editing > Convert to offline project*. Keep the layer selected and click *OK*.",
                           isVerifyStep=True)
    offlineTest.addStep("Enable editing on the recently added layer. Activate the layer in the *Layers* panel and enable editing."
                        " In the *Digitizing toolbar* (in the second row of menu icons), click the *Toggle editing* icon (it's a pencil)"
                         "or from menus go to *Layer > Toogle Editing* This will allow you to edit the layer.",
                           isVerifyStep=True)
    offlineTest.addStep("Click the *Add Feature* icon in the same toolbar.",
                           isVerifyStep=True)
    offlineTest.addStep('''
Click once anywhere in the viewer window - this sets the first vertex of the polygon. Keep clicking other places to add more vertices.

*on OS X*:
to finish the polygon hold the control key down and click (this will add one last vertex).

*on Windows*:
use the right mouse button to end (no other vertex is added).

When you complete the polygon a *Feature Attributes* dialog will pop-up.

Simply click the *Ok* button to dismiss it.
''',
                           isVerifyStep=True)
    offlineTest.addStep("Click the *Save Layer Edits* icon or go to *Layer > Save Layer Edits* menu.",
                           isVerifyStep=True)
    offlineTest.addStep("Click the *Toggle Editing* icon or select the 'Toggle Editing' menu item under Layer.",
                           isVerifyStep=True)
    offlineTest.addStep("Sync the project by selecting *Database > Offline editing > Synchronize*",
                           isVerifyStep=True)    
    offlineTest.addStep("Verify that your changes were stored on the GeoServer. Compare the edited layer with the new one, and verify that they are identical.",
                           prestep= lambda: _loadWfsToBeEdited("testlayer_afterediting"), isVerifyStep=True)    

    return [spatialiteTest, logTest, aboutTest, wcsTest, wfsTest, arcmapTest, arcfeatureTest, postgisTest, offlineTest]

def settings():
    return  {TEST_URLS: "https://suite410.boundless.test:8444/geoserver/web/, "
                        "http://suite410.boundless.test:8082/geoserver/web/, "
                        "https://server100.boundless.test:8445/geoserver/web/, "
                        "http://server100.boundless.test:8084/geoserver/web/, "
                        "https://server.boundless.test:8443/geoserver/web/, "
                        "http://server.boundless.test:8080/geoserver/web/ "}


def unitTests():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(PackageTests))
    suite.addTests(unittest.makeSuite(TestImports))
    suite.addTests(unittest.makeSuite(TestSupportedFormats))
    suite.addTests(unittest.makeSuite(TestOtherCommandLineUtilities))
    return suite


def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(unitTests())

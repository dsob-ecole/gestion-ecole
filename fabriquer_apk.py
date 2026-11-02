# GestionÉcole — fabrique le projet Android (APK) à partir des fichiers de l'application.
# Ce fichier est lancé par GitHub (fichier .github/workflows/apk.yml) : vous n'avez pas à le lancer vous-même.
# Il ne contient aucun secret : la clé de signature arrive par le « secret » CLE_APK du compte GitHub.
import base64, os, shutil, sys

NUMERO = int(os.environ.get("NUMERO", "1"))
CLE = os.environ.get("CLE_APK", "").strip()
MOT_DE_PASSE = "GestionEcole-DSOB-apk"          # protège le fichier de la clé ; la clé elle-même reste secrète
PAQUET = "sn.dsob.gestionecole"
P = "apk_projet"

if not CLE:
    sys.exit("ERREUR : le secret CLE_APK n'est pas installé dans GitHub (Settings > Secrets and variables > Actions).")

shutil.rmtree(P, ignore_errors=True)


def ecrire(chemin, texte):
    chemin = os.path.join(P, chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(texte.lstrip("\n"))


def copier(source, chemin):
    chemin = os.path.join(P, chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    shutil.copyfile(source, chemin)


with open(os.path.join(os.makedirs(P, exist_ok=True) or P, "cle.p12"), "wb") as f:
    f.write(base64.b64decode("".join(CLE.split())))

ecrire("settings.gradle", """
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "GestionEcole"
include ':app'
""")

ecrire("build.gradle", """
plugins { id 'com.android.application' version '8.5.2' apply false }
""")

ecrire("gradle.properties", """
android.useAndroidX=true
org.gradle.jvmargs=-Xmx2g
""")

ecrire("app/build.gradle", """
plugins { id 'com.android.application' }

android {
    namespace '%(paquet)s'
    compileSdk 34
    defaultConfig {
        applicationId '%(paquet)s'
        minSdk 24
        targetSdk 34
        versionCode %(numero)d
        versionName "1.%(numero)d"
    }
    signingConfigs {
        release {
            storeFile file('../cle.p12')
            storePassword '%(mdp)s'
            keyAlias 'dsob'
            keyPassword '%(mdp)s'
            storeType 'pkcs12'
        }
    }
    buildTypes {
        release {
            minifyEnabled false
            signingConfig signingConfigs.release
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}

dependencies {
    implementation 'androidx.webkit:webkit:1.11.0'
    implementation 'androidx.core:core:1.13.1'
}
""" % {"paquet": PAQUET, "numero": NUMERO, "mdp": MOT_DE_PASSE})

ecrire("app/src/main/AndroidManifest.xml", """
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="GestionÉcole"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="false"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="portrait"
            android:configChanges="orientation|screenSize|keyboardHidden|keyboard|screenLayout|uiMode"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="%(paquet)s.fichiers"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/chemins" />
        </provider>
    </application>
</manifest>
""" % {"paquet": PAQUET})

ecrire("app/src/main/res/xml/chemins.xml", """
<?xml version="1.0" encoding="utf-8"?>
<paths>
    <cache-path name="envois" path="envois/" />
</paths>
""")

ecrire("app/src/main/java/sn/dsob/gestionecole/MainActivity.java", """
package sn.dsob.gestionecole;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

// L'application du téléphone (index.html) est rangée DANS l'APK : elle marche sans Internet.
public class MainActivity extends Activity {
    private static final int CHOIX_FICHIER = 7;
    private WebView web;
    private ValueCallback<Uri[]> choix;

    @Override
    protected void onCreate(Bundle etat) {
        super.onCreate(etat);
        getWindow().setStatusBarColor(0xFFC62828);
        web = new WebView(this);
        setContentView(web);
        WebSettings r = web.getSettings();
        r.setJavaScriptEnabled(true);
        r.setDomStorageEnabled(true);          // la classe et les notes restent dans le téléphone
        r.setAllowFileAccess(false);
        r.setAllowContentAccess(true);
        final WebViewAssetLoader chargeur = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this)).build();
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest q) {
                return chargeur.shouldInterceptRequest(q.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest q) {
                Uri u = q.getUrl();
                if ("appassets.androidplatform.net".equals(u.getHost())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> rappel, FileChooserParams p) {
                if (choix != null) choix.onReceiveValue(null);
                choix = rappel;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(i, "Choisir le fichier de la classe"), CHOIX_FICHIER);
                } catch (Exception e) {
                    choix = null;
                    return false;
                }
                return true;
            }
        });
        web.addJavascriptInterface(new Pont(), "Android");
        if (etat != null) web.restoreState(etat);
        else web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle etat) {
        super.onSaveInstanceState(etat);
        web.saveState(etat);
    }

    @Override
    protected void onActivityResult(int code, int resultat, Intent donnees) {
        super.onActivityResult(code, resultat, donnees);
        if (code != CHOIX_FICHIER || choix == null) return;
        Uri[] r = null;
        if (resultat == RESULT_OK && donnees != null && donnees.getData() != null) r = new Uri[]{donnees.getData()};
        choix.onReceiveValue(r);
        choix = null;
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("(window.retourAndroid ? retourAndroid() : false)", v -> {
            if (!"true".equals(v)) finish();
        });
    }

    // Envoyer les notes : le fichier part par WhatsApp (ou mail, Bluetooth…)
    public class Pont {
        @JavascriptInterface
        public void partager(final String nom, final String texte) {
            runOnUiThread(() -> {
                try {
                    File dossier = new File(getCacheDir(), "envois");
                    dossier.mkdirs();
                    File f = new File(dossier, nom.replaceAll("[^A-Za-z0-9._-]", "_"));
                    try (FileOutputStream o = new FileOutputStream(f)) {
                        o.write(texte.getBytes(StandardCharsets.UTF_8));
                    }
                    Uri u = FileProvider.getUriForFile(MainActivity.this, "%(paquet)s.fichiers", f);
                    Intent i = new Intent(Intent.ACTION_SEND);
                    i.setType("application/octet-stream");
                    i.putExtra(Intent.EXTRA_STREAM, u);
                    i.putExtra(Intent.EXTRA_TEXT, "Notes de ma classe (fichier pour le directeur)");
                    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(i, "Envoyer les notes au directeur"));
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Envoi impossible : " + e.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
        }
    }
}
""".replace("%(paquet)s", PAQUET))

# l'application elle-même, rangée dans l'APK
for nom in ("index.html", "manifest.webmanifest", "icone-192.png", "icone-512.png"):
    copier(nom, "app/src/main/assets/" + nom)
copier("icone-192.png", "app/src/main/res/mipmap-xxxhdpi/ic_launcher.png")
print("Projet Android prêt : version 1." + str(NUMERO))

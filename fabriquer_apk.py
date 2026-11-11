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
    <!-- seulement pour voir s'il existe une nouvelle version (aucune donnée n'est envoyée) -->
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:label="GestionÉcole"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="false"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTask"
            android:screenOrientation="portrait"
            android:configChanges="orientation|screenSize|keyboardHidden|keyboard|screenLayout|uiMode"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
            <!-- fichier « Classe_… .classe » touché dans WhatsApp : « Ouvrir avec GestionÉcole » -->
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="application/octet-stream" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:scheme="content" />
                <data android:mimeType="application/classe" />
            </intent-filter>
            <!-- appui long sur le fichier, puis « Partager » > GestionÉcole -->
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="*/*" />
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
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import android.graphics.Canvas;
import android.graphics.pdf.PdfDocument;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

// L'application du téléphone (index.html) est rangée DANS l'APK : elle marche sans Internet.
public class MainActivity extends Activity {
    private static final int CHOIX_FICHIER = 7;
    private WebView web;
    private FrameLayout conteneur;
    private ValueCallback<Uri[]> choix;
    private String attenteNom = null, attenteTexte = null;     // fichier reçu de WhatsApp, en attente du code

    @Override
    protected void onCreate(Bundle etat) {
        super.onCreate(etat);
        getWindow().setStatusBarColor(0xFFC62828);
        WebView.enableSlowWholeDocumentDraw();      // étape 305 : pour dessiner toute la page des fiches dans le PDF
        web = new WebView(this);
        conteneur = new FrameLayout(this);
        conteneur.addView(web, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(conteneur);
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
        lireIntent(getIntent());
        if (etat != null) web.restoreState(etat);
        else web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
    }

    @Override
    protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        setIntent(i);
        if (lireIntent(i)) web.evaluateJavascript("(window.verifierFichierAndroid && verifierFichierAndroid())", null);
    }

    // Lit le fichier touché (ou partagé) dans WhatsApp ; la page le prendra avec Android.fichierEnAttente()
    private synchronized boolean lireIntent(Intent i) {
        if (i == null) return false;
        Uri u = null;
        if (Intent.ACTION_VIEW.equals(i.getAction())) u = i.getData();
        else if (Intent.ACTION_SEND.equals(i.getAction())) u = i.getParcelableExtra(Intent.EXTRA_STREAM);
        if (u == null) return false;
        try (InputStream in = getContentResolver().openInputStream(u)) {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] t = new byte[8192];
            int n;
            while ((n = in.read(t)) > 0) {
                b.write(t, 0, n);
                if (b.size() > 30000000) break;
            }
            attenteTexte = new String(b.toByteArray(), StandardCharsets.UTF_8);
            attenteNom = nomDuFichier(u);
            i.setAction(Intent.ACTION_MAIN);          // ne pas relire le même fichier en tournant l'écran
            return true;
        } catch (Exception e) {
            Toast.makeText(this, "Impossible de lire ce fichier : " + e.getMessage(), Toast.LENGTH_LONG).show();
            return false;
        }
    }

    private String nomDuFichier(Uri u) {
        try (Cursor c = getContentResolver().query(u, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int k = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (k >= 0) return c.getString(k);
            }
        } catch (Exception e) { }
        String p = u.getLastPathSegment();
        return p == null ? "" : p;
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
        public int version() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
            } catch (Exception e) {
                return 0;
            }
        }

        @JavascriptInterface
        public String fichierEnAttente() {
            synchronized (MainActivity.this) {
                if (attenteTexte == null) return "";
                try {
                    String r = new JSONObject().put("nom", attenteNom).put("texte", attenteTexte).toString();
                    attenteTexte = null;
                    attenteNom = null;
                    return r;
                } catch (Exception e) {
                    return "";
                }
            }
        }

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

        // Étape 305 : les fiches cochées -> un PDF A4 (avec les données pour l'ordinateur du directeur), envoyé par WhatsApp
        @JavascriptInterface
        public void fairePdf(final String nom, final String html, final String donnees) {
            runOnUiThread(() -> new FabriquePdf(nom, html, donnees).demarrer());
        }
    }

    private class FabriquePdf {
        final int LARGEUR = 794, HAUTEUR = 1123;        // une page A4 en points d'écran (96 par pouce)
        final String nom, html, donnees;
        final float densite = getResources().getDisplayMetrics().density;
        WebView w;
        boolean fini = false;

        FabriquePdf(String nom, String html, String donnees) { this.nom = nom; this.html = html; this.donnees = donnees; }

        int px(int css) { return Math.round(css * densite); }

        void demarrer() {
            try {
                w = new WebView(MainActivity.this);
                WebSettings r = w.getSettings();
                r.setJavaScriptEnabled(true);
                r.setTextZoom(100);
                r.setAllowFileAccess(false);
                w.setVerticalScrollBarEnabled(false);
                w.setHorizontalScrollBarEnabled(false);
                conteneur.addView(w, 0, new FrameLayout.LayoutParams(px(LARGEUR), px(HAUTEUR)));   // derrière l'application
                w.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView v, String url) {
                        if (fini) return;
                        fini = true;
                        w.postDelayed(() -> paginer(), 500);
                    }
                });
                Toast.makeText(MainActivity.this, "Préparation du PDF…", Toast.LENGTH_SHORT).show();
                w.loadDataWithBaseURL("https://appassets.androidplatform.net/assets/", html, "text/html", "utf-8", null);
            } catch (Exception e) {
                echec(e);
            }
        }

        void paginer() {
            w.evaluateJavascript("paginerPourPdf()", v -> {
                try {
                    int pages = Math.max(1, Integer.parseInt(v.replaceAll("[^0-9]", "")));
                    w.setLayoutParams(new FrameLayout.LayoutParams(px(LARGEUR), px(HAUTEUR * pages)));
                    w.postDelayed(() -> dessiner(pages), 900);
                } catch (Exception e) {
                    echec(e);
                }
            });
        }

        void dessiner(int pages) {
            PdfDocument doc = new PdfDocument();
            try {
                float echelle = 595f / px(LARGEUR);
                for (int p = 0; p < pages; p++) {
                    PdfDocument.Page page = doc.startPage(new PdfDocument.PageInfo.Builder(595, 842, p + 1).create());
                    Canvas c = page.getCanvas();
                    c.scale(echelle, echelle);
                    c.translate(0, -p * HAUTEUR * densite);
                    w.draw(c);
                    doc.finishPage(page);
                }
                File dossier = new File(getCacheDir(), "envois");
                dossier.mkdirs();
                File f = new File(dossier, nom.replaceAll("[^A-Za-z0-9._-]", "_"));
                try (FileOutputStream o = new FileOutputStream(f)) {
                    doc.writeTo(o);
                    // après la fin du PDF : les fiches en texte, pour l'ordinateur du directeur (les lecteurs PDF l'ignorent)
                    o.write(("\n%DSOB-FICHES " + donnees + "\n").getBytes(StandardCharsets.US_ASCII));
                }
                doc.close();
                retirer();
                Uri u = FileProvider.getUriForFile(MainActivity.this, "%(paquet)s.fichiers", f);
                Intent i = new Intent(Intent.ACTION_SEND);
                i.setType("application/pdf");
                i.putExtra(Intent.EXTRA_STREAM, u);
                i.putExtra(Intent.EXTRA_TEXT, "Mes fiches de préparation");
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivity(Intent.createChooser(i, "Envoyer les fiches au directeur"));
            } catch (Exception e) {
                try { doc.close(); } catch (Exception x) { }
                echec(e);
            }
        }

        void retirer() {
            try { conteneur.removeView(w); w.destroy(); } catch (Exception e) { }
        }

        void echec(Exception e) {
            retirer();
            Toast.makeText(MainActivity.this, "PDF impossible (" + e.getMessage() + ") : les fiches partent en page web.", Toast.LENGTH_LONG).show();
            web.evaluateJavascript("(window.pdfEchec && pdfEchec())", null);
        }
    }
}
""".replace("%(paquet)s", PAQUET))

# l'application elle-même, rangée dans l'APK
for nom in ("index.html", "manifest.webmanifest", "icone-192.png", "icone-512.png",
            "contenu_CE1.bin", "contenu_CE2.bin", "contenu_CM1.bin", "contenu_CM2.bin"):     # étape 305 : les fiches
    copier(nom, "app/src/main/assets/" + nom)
copier("icone-192.png", "app/src/main/res/mipmap-xxxhdpi/ic_launcher.png")
print("Projet Android prêt : version 1." + str(NUMERO))

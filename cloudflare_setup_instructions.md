# Ghid de Configurare Conectivitate Cloudflare pentru Sincronizare Online

Acest ghid oferă instrucțiuni pas cu pas despre cum să configurezi **Cloudflare Workers** și **Cloudflare KV (Key-Value)** pentru a găzdui baza de date a aplicației de inventar online. Această configurare îți va permite să lucrezi direct de pe laptop sau de pe orice alt dispozitiv, având datele sincronizate în timp real în cloud.

---

## 1. Ce este Cloudflare KV și Cloudflare Workers?

- **Cloudflare KV**: O bază de date distribuită de tip Cheie-Valoare (Key-Value), extrem de rapidă, perfectă pentru stocarea stării sau configurației JSON a aplicației tale.
- **Cloudflare Workers**: Serverless functions (cod Javascript/Typescript) care rulează pe serverele Cloudflare de la marginea rețelei (Edge). Worker-ul va acționa ca un API intermediar (REST API) care preia datele din aplicație prin metoda `POST` și le salvează în KV, respectiv le trimite înapoi către aplicație prin metoda `GET`.

---

## 2. Pasul 1: Crearea unui cont Cloudflare și crearea bazei de date KV

1. Conectează-te la panoul de control [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. În meniul din stânga, mergi la **Workers & Pages** -> **KV**.
3. Apasă pe butonul **Create Namespace** (sau *Create a Namespace*).
4. Introdu un nume sugestiv pentru baza de date (de exemplu: `INVENTORY_KV`) și apasă pe **Add** / **Create**.
5. Notează-ți **ID-ul Namespace-ului** generat (un șir lung de caractere hexadecimale, ex: `9a8b7c6d5e4f...`), deoarece vei avea nevoie de el la configurarea Worker-ului.

---

## 3. Pasul 2: Crearea și configurarea Worker-ului Cloudflare

Worker-ul va procesa cererile HTTP `GET` (pentru a citi inventarul) și `POST` (pentru a-l actualiza), ocupându-se totodată și de regulile **CORS** (pentru a permite accesul de pe laptop-ul tău local sau dintr-o pagină locală HTML).

### Opțiunea A: Direct din interfața Web Cloudflare (Fără instalare CLI)

1. În panoul Cloudflare, accesează **Workers & Pages** -> **Overview**.
2. Apasă pe **Create Application** (sau *Create Worker*).
3. Selectează **Create Worker**, dă-i un nume prietenos (de exemplu: `inventory-api`) și apasă pe **Deploy**.
4. După creare, apasă pe butonul **Edit Code** pentru a deschide editorul online (Quick Edit).
5. Înlocuiește tot codul din editor cu scriptul JavaScript de mai jos:

```javascript
// Cod JavaScript pentru Cloudflare Worker (Găzduire API Inventar)

const SECRET_KEY = "PAROLA_TA_AICI"; // Înlocuiește cu o parolă sigură pentru securizarea API-ului

export default {
  async fetch(request, env, ctx) {
    // Definire Headere CORS pentru a permite accesul de pe laptop (file:// sau localhost)
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    // Gestionare cereri de tip OPTIONS (Preflight pentru CORS)
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: corsHeaders
      });
    }

    // URL-ul rutei apelate
    const url = new URL(request.url);

    // Verifică cheia de securizare dacă este configurată
    const authHeader = request.headers.get("Authorization");
    const token = authHeader ? authHeader.replace("Bearer ", "") : null;

    if (SECRET_KEY && token !== SECRET_KEY) {
      return new Response(JSON.stringify({ error: "Neautorizat. Cheia de securitate lipsește sau este incorectă." }), {
        status: 401,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }

    // Baza de date KV legată la Worker (trebuie mapată ca variabilă de mediu "INVENTORY_STORE")
    const kvStore = env.INVENTORY_STORE;
    if (!kvStore) {
      return new Response(JSON.stringify({ error: "Baza de date KV (INVENTORY_STORE) nu este mapată corect la Worker." }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }

    const KV_KEY = "inventory_config_data";

    // METODA GET: Citește datele din KV și le trimite înapoi în format JSON
    if (request.method === "GET") {
      let data = await kvStore.get(KV_KEY);

      // Dacă baza de date este goală, returnăm o structură inițială goală
      if (!data) {
        const initialConfig = {
          locations: ["IT Genetics", "SmartID", "Scancode", "Depozit Central", "Bogdan", "Nicusor"],
          serialNumbers: {},
          records: []
        };
        data = JSON.stringify(initialConfig);
      }

      return new Response(data, {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }

    // METODA POST: Primește datele JSON de la aplicație și le salvează în KV
    if (request.method === "POST") {
      try {
        const payload = await request.json();

        // Validăm minimal structura JSON primită
        if (!payload || !Array.isArray(payload.locations)) {
          return new Response(JSON.stringify({ error: "Structură JSON invalidă." }), {
            status: 400,
            headers: { "Content-Type": "application/json", ...corsHeaders }
          });
        }

        // Salvare în Cloudflare KV
        await kvStore.put(KV_KEY, JSON.stringify(payload));

        return new Response(JSON.stringify({ success: true, message: "Datele au fost salvate cu succes!" }), {
          status: 200,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: "Eroare la procesarea cererii: " + err.message }), {
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      }
    }

    // Răspuns implicit pentru metode nesuportate
    return new Response(JSON.stringify({ error: "Metodă nesuportată. Folosiți GET sau POST." }), {
      status: 405,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }
};
```

6. Apasă pe **Save and Deploy** în colțul din dreapta sus.

---

## 4. Pasul 3: Maparea bazei de date KV la Worker (Crucial!)

Pentru ca Worker-ul tău să poată citi și scrie în baza de date KV pe care ai creat-o la Pasul 1, trebuie să le conectezi (să definești variabila de mediu `INVENTORY_STORE`):

1. În panoul Worker-ului nou creat (`inventory-api`), mergi la tab-ul **Settings**.
2. Selectează sub-meniul **Bindings** (sau în funcție de interfață, direct în **Variables** -> secțiunea **KV Namespace Bindings**).
3. Apasă pe **Add** -> **KV Namespace**.
4. Configurează legătura:
   - **Variable name**: Trebuie să fie exact `INVENTORY_STORE` (cu litere mari, fix așa cum apare în codul JS).
   - **KV Namespace**: Selectează din listă Namespace-ul creat anterior (ex: `INVENTORY_KV`).
5. Apasă pe **Save** / **Deploy**.

---

## 5. Pasul 4: Conectarea aplicației din browser (Laptop local)

Acum ai un API online complet funcțional! Adresa URL a Worker-ului tău va fi de forma:
`https://inventory-api.<numele-tau-de-subdomeniu>.workers.dev`

Pentru a conecta aplicația de pe laptop:

1. Deschide fișierul `inventory_hosted_en 1.2.html` pe laptop.
2. În colțul din dreapta sus al paginii web, apasă pe pictograma în formă de rotiță din stânga butonului albastru "Save Config" (**Cloud Connection Settings**). De asemenea, poți apăsa pe linkul "Configure API URL" din banner-ul de alertă portocaliu de sus.
3. Completează câmpurile:
   - **Cloud API URL**: Adresa completă a Worker-ului tău (ex: `https://inventory-api.username.workers.dev`).
   - **Security Key / Password**: Parola pe care ai configurat-o în codul Worker-ului în variabila `SECRET_KEY` (ex: `PAROLA_TA_AICI`).
4. Apasă pe butonul **Save Config** din colțul din dreapta sus pentru a iniția prima sincronizare.
5. Din acest moment, aplicația se va conecta automat în Cloud (vei vedea indicatorul verde **"Connected to Cloud"**). Toate modificările, adăugările, editările sau ștergerile vor fi sincronizate instant în baza de date Cloudflare.

---

## 6. Rezumatul fluxului de lucru

- Când deschizi aplicația pe laptop, aceasta face un apel HTTP `GET` securizat către Cloudflare Worker. Worker-ul preia datele din KV și ți le afișează.
- Când modifici sau adaugi un echipament și apeși **Save Config** (sau la orice adăugare/editare), aplicația trimite un `POST` securizat cu noul JSON actualizat.
- Baza de date este stocată în cloud-ul securizat Cloudflare, iar aplicația funcționează de oriunde ai conexiune la internet, fără a depinde de un server fizic acasă sau la birou!

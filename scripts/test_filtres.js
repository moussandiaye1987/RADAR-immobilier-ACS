// Ouvre index.html dans Chromium et vérifie que la page et ses filtres fonctionnent
// avec les données de annonces.json.
// Usage : NODE_PATH=$(npm root -g) node scripts/test_filtres.js
// Les nombres attendus sont recalculés ici à partir des données, avec les mêmes règles
// que la fonction matches() de index.html. Code de sortie 1 si un contrôle échoue.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const racine = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(racine, 'annonces.json'), 'utf8'));
const visibles = data.rows.filter(r => r.statut !== 'vendu');
const DEFAUT = { bMin: 300000, bMax: 2000000, sMin: 250 };
const parDefaut = visibles.filter(r =>
  (r.prix == null || (r.prix >= DEFAUT.bMin && r.prix <= DEFAUT.bMax)) && (r.surface || 0) >= DEFAUT.sMin);
const port = 8000 + Math.floor(Math.random() * 900);
const echecs = [];
const verifier = (nom, obtenu, attendu) => {
  const ok = String(obtenu) === String(attendu);
  console.log(`${ok ? 'OK    ' : 'ÉCHEC '} ${nom} : ${obtenu}${ok ? '' : ` (attendu ${attendu})`}`);
  if (!ok) echecs.push(nom);
};

async function lancer(executablePath) {
  try { return await chromium.launch(executablePath ? { executablePath } : {}); } catch (e) { return null; }
}

(async () => {
  const serveur = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', racine], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 1000));
  const navigateur = (await lancer('/opt/pw-browsers/chromium-1194/chrome-linux/chrome')) || (await lancer());
  if (!navigateur) { console.log('ÉCHEC Chromium introuvable'); serveur.kill(); process.exit(1); }
  const page = await (await navigateur.newContext()).newPage();
  const erreursJs = [];
  page.on('pageerror', e => erreursJs.push(e.message));
  try {
    await page.goto(`http://127.0.0.1:${port}/index.html`);
    await page.waitForTimeout(1000);
    const compte = async () => Number((await page.textContent('#kCount')).trim());
    const puce = (zone, texte) => page.locator(`#${zone} button`, { hasText: texte }).first();

    verifier('bandeau', (await page.textContent('#snap')).trim(), `Données relevées le ${data.date} (${data.rows.length} annonces).`);
    verifier('annonces affichées (filtres par défaut)', await compte(), parDefaut.length);
    verifier('fiches affichées (filtres par défaut)', await page.locator('#list article.card').count(), parDefaut.length);

    await page.fill('#bMin', '0');
    await page.fill('#bMax', '999999999');
    await page.$eval('#sMin', e => { e.value = 0; e.dispatchEvent(new Event('input', { bubbles: true })); });
    verifier('annonces sans limite de budget ni de surface', await compte(), visibles.length);
    verifier('étiquettes « Nouveau »', await page.locator('.tag.new').count(), visibles.filter(r => r.nouveau).length);

    for (const d of ['75', '77', '78', '91', '92', '93', '94', '95']) {
      await puce('deptChips', d).click();
      verifier(`filtre département ${d}`, await compte(), visibles.filter(r => r.dept === d).length);
      await puce('deptChips', d).click();
    }
    for (const m of ['Métro', 'RER', 'Tram', 'Transilien', 'Bus']) {
      await puce('modeChips', m).click();
      verifier(`filtre transport ${m}`, await compte(), visibles.filter(r => (r.transports || []).some(t => t.mode === m)).length);
      await puce('modeChips', m).click();
    }
    for (const [cle, libelle, cls] of [['L', 'Type L confirmé', 'l'], ['ERP', 'ERP déclaré', 'erp'], ['verifier', 'ERP à vérifier', 'chk']]) {
      await puce('erpChips', libelle).click();
      verifier(`filtre statut ERP « ${libelle} »`, await compte(), visibles.filter(r => r.erp === cle).length);
      // Chaque fiche du filtre affiche l'étiquette exacte de son statut.
      verifier(`étiquette « ${libelle} » affichée sur chaque fiche`,
        await page.locator(`#list article.card .tag.${cls}`).filter({ hasText: new RegExp(`^${libelle}$`) }).count(), visibles.filter(r => r.erp === cle).length);
      await puce('erpChips', libelle).click();
    }
    verifier('statuts ERP des données reconnus', visibles.filter(r => !['L', 'ERP', 'verifier'].includes(r.erp)).length, 0);
    await page.click('[data-park="sur_place"]');
    verifier('filtre parking sur place', await compte(), visibles.filter(r => r.parking === 'sur_place').length);
    await page.click('[data-park="near"]');
    verifier('filtre parking sur place ou proche', await compte(), visibles.filter(r => ['sur_place', 'proximite'].includes(r.parking)).length);
    await page.click('[data-park="any"]');
    await page.check('#onlyConfirmed');
    verifier('filtre desserte confirmée', await compte(), visibles.filter(r => (r.transports || []).some(t => t.confirme)).length);
    await page.uncheck('#onlyConfirmed');

    for (const tri of await page.$$eval('#sort option', o => o.map(x => x.value))) {
      await page.selectOption('#sort', tri);
      verifier(`tri « ${tri} » (fiches affichées)`, await page.locator('#list article.card').count(), visibles.length);
    }
    await page.click('#resetBtn');
    verifier('bouton de réinitialisation', await compte(), parDefaut.length);
    verifier('erreurs JavaScript', erreursJs.length, 0);
  } catch (e) {
    console.log('ÉCHEC ' + e.message.split('\n')[0]);
    echecs.push('exception');
  }
  await navigateur.close();
  serveur.kill();
  console.log(echecs.length ? `Test des filtres : ${echecs.length} échec(s)` : 'Test des filtres : OK');
  process.exit(echecs.length ? 1 : 0);
})();

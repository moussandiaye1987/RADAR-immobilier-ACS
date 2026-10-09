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
  const contexte = await navigateur.newContext();
  // Pas de réseau externe pendant les tests : les fonds de carte OpenStreetMap sont neutralisés.
  await contexte.route('**/tile.openstreetmap.org/**', r => r.abort());
  const page = await contexte.newPage();
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

    // ---- Carte Leaflet : bouton Liste / Carte, repères, fiche, regroupement, synchronisation avec les filtres ----
    const marqueurs = async () => Number(await page.getAttribute('#mapInfo', 'data-markers'));
    const visible = sel => page.locator(sel).isVisible();
    verifier('affichage par défaut : liste visible, carte masquée', [await visible('#list'), await visible('#mapWrap')].join(','), 'true,false');
    await page.click('[data-view="map"]');
    await page.waitForFunction(() => document.getElementById('mapInfo').dataset.markers !== undefined, null, { timeout: 15000 });
    verifier('carte visible, liste masquée', [await visible('#list'), await visible('#mapWrap')].join(','), 'false,true');
    verifier('bouton « Carte » activé', await page.getAttribute('[data-view="map"]', 'aria-pressed'), 'true');
    const centre = await page.evaluate(() => { const c = window.radarMap.map.getCenter(); return [c.lat, c.lng]; });
    verifier('carte centrée sur l\'Île-de-France', centre[0] > 48.3 && centre[0] < 49.1 && centre[1] > 1.8 && centre[1] < 3.2, true);
    verifier('repères = annonces filtrées (filtres par défaut)', await marqueurs(), parDefaut.length);
    verifier('annonces sans position', await page.getAttribute('#mapInfo', 'data-unlocated'), '0');
    verifier('repères regroupés (grappes visibles)', (await page.locator('.marker-cluster').count()) > 0, true);
    verifier('attribution OpenStreetMap affichée', (await page.locator('.leaflet-control-attribution').textContent()).includes('OpenStreetMap'), true);

    // Synchronisation avec chaque famille de filtres : le nombre de repères suit toujours le nombre d'annonces affichées.
    const synchro = async nom => verifier(`carte synchronisée : ${nom}`, await marqueurs(), await compte());
    await puce('deptChips', '94').click(); await synchro('département 94');
    verifier('  … attendu (département 94)', await marqueurs(), parDefaut.filter(r => r.dept === '94').length);
    await puce('deptChips', '94').click();
    await puce('erpChips', 'ERP à vérifier').click(); await synchro('statut ERP à vérifier');
    verifier('  … attendu (ERP à vérifier)', await marqueurs(), parDefaut.filter(r => r.erp === 'verifier').length);
    await puce('erpChips', 'ERP à vérifier').click();
    await page.$eval('#sMin', e => { e.value = 600; e.dispatchEvent(new Event('input', { bubbles: true })); }); await synchro('surface ≥ 600 m²');
    verifier('  … attendu (surface ≥ 600)', await marqueurs(), visibles.filter(r => (r.prix == null || (r.prix >= DEFAUT.bMin && r.prix <= DEFAUT.bMax)) && (r.surface || 0) >= 600).length);
    await page.fill('#bMax', '800000'); await synchro('budget max 800 000 €');
    await page.click('[data-park="sur_place"]'); await synchro('parking sur place');
    await puce('modeChips', 'RER').click(); await synchro('transport RER');
    await page.$eval('#sMin', e => { e.value = 0; e.dispatchEvent(new Event('input', { bubbles: true })); });
    await page.fill('#bMin', '0'); await page.fill('#bMax', '999999999');
    await page.click('[data-park="any"]'); await puce('modeChips', 'RER').click();
    await synchro('sans limite'); verifier('  … attendu (tout)', await marqueurs(), visibles.length);
    await page.fill('#bMax', '1'); await page.uncheck('#incNoPrice');
    verifier('carte vide quand aucun résultat', await marqueurs(), 0);
    await page.click('#resetBtn'); await synchro('réinitialisation');
    verifier('  … attendu (réinitialisation)', await marqueurs(), parDefaut.length);

    // Fiche au clic : prix, surface, ville, statut ERP, lien de l'annonce ; position approximative signalée.
    const infoPopup = await page.evaluate(() => new Promise(ok => {
      const m = window.radarMap.layer.getLayers()[0];
      window.radarMap.layer.zoomToShowLayer(m, () => { m.openPopup(); ok(document.querySelector('.leaflet-popup-content').innerText + '\n@@' + (document.querySelector('.leaflet-popup-content a') || {}).href); });
    }));
    const [texte, lien] = infoPopup.split('\n@@');
    const ligne = data.rows.find(r => r.url === lien);
    verifier('fiche : lien de l\'annonce', Boolean(ligne), true);
    if (ligne) {
      const libelle = { L: 'Type L confirmé', ERP: 'ERP déclaré', verifier: 'ERP à vérifier' }[ligne.erp];
      verifier('fiche : ville', texte.includes(ligne.ville), true);
      verifier('fiche : statut ERP exact', texte.includes(libelle), true);
      verifier('fiche : surface', texte.replace(/\s/g, ' ').includes(`${ligne.surface} m²`), true);
      verifier('fiche : prix', ligne.prix == null ? texte.includes('Prix sur demande') : texte.replace(/[\s  ]/g, '').includes(String(ligne.prix).replace(/\B(?=(\d{3})+(?!\d))/g, '')) , true);
      verifier('fiche : position approximative signalée', texte.includes('Position approximative'), true);
    }
    // Coordonnées exactes présentes dans les données : elles priment sur le centre de la commune.
    const exact = await page.evaluate(id => { const r = rows.find(x => x._id === id); r.lat = 48.9; r.lng = 2.05; render();
      const m = window.radarMap.layer.getLayers().find(x => Math.abs(x.getLatLng().lat - 48.9) < 1e-9 && Math.abs(x.getLatLng().lng - 2.05) < 1e-9);
      return Boolean(m) && !m.getPopup().getContent().includes('Position approximative'); }, parDefaut[0]._id);
    verifier('coordonnées exactes utilisées sans mention « approximative »', exact, true);
    await page.evaluate(id => { const r = rows.find(x => x._id === id); delete r.lat; delete r.lng; }, parDefaut[0]._id);

    // Retour à la liste : affichage d'origine inchangé.
    await page.click('[data-view="list"]');
    verifier('retour à la liste : liste visible, carte masquée', [await visible('#list'), await visible('#mapWrap')].join(','), 'true,false');
    verifier('retour à la liste : fiches affichées', await page.locator('#list article.card').count(), parDefaut.length);

    // Mobile : la carte tient dans l'écran, sans défilement horizontal.
    const mobile = await (await navigateur.newContext({ viewport: { width: 390, height: 800 }, isMobile: true, hasTouch: true })).newPage();
    await mobile.context().route('**/tile.openstreetmap.org/**', r => r.abort());
    const erreursMobile = [];
    mobile.on('pageerror', e => erreursMobile.push(e.message));
    await mobile.goto(`http://127.0.0.1:${port}/index.html`);
    await mobile.waitForTimeout(500);
    await mobile.click('[data-view="map"]');
    await mobile.waitForFunction(() => document.getElementById('mapInfo').dataset.markers !== undefined, null, { timeout: 15000 });
    const dims = await mobile.evaluate(() => ({ l: document.getElementById('map').getBoundingClientRect().width, w: window.innerWidth, sw: document.documentElement.scrollWidth }));
    verifier('mobile : la carte tient dans l\'écran', dims.l <= dims.w && dims.l > 200, true);
    verifier('mobile : pas de défilement horizontal', dims.sw <= dims.w, true);
    verifier('mobile : repères affichés', Number(await mobile.getAttribute('#mapInfo', 'data-markers')), parDefaut.length);
    verifier('mobile : erreurs JavaScript', erreursMobile.length, 0);

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

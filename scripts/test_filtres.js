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
// Par défaut, le site masque les annonces vendues et les annonces archivées (case « Afficher les annonces archivées »).
const nonVendues = data.rows.filter(r => r.statut !== 'vendu');
const visibles = nonVendues.filter(r => !r.archive);
const archivees = nonVendues.filter(r => r.archive);
// Classement ERP affiché (même règle que statut() dans index.html) : « ERP à vérifier » tant qu'aucun type n'est confirmé.
const STATUTS = [['declare', 'ERP déclaré (type confirmé)', 'l'], ['V', 'Type V confirmé', 'v'], ['L', 'Type L confirmé', 'l'], ['verifier', 'ERP à vérifier', 'chk']];
const declares = r => { const d = [...(r.typesDeclares || [])]; if ((r.erp === 'V' || r.erp === 'L') && !d.includes(r.erp)) d.push(r.erp); return d; };
const statut = r => (r.erp === 'V' || r.erp === 'L' ? r.erp : (declares(r).length ? 'declare' : 'verifier'));
const etiquette = r => (statut(r) === 'declare' ? `ERP déclaré : type ${declares(r).join(', ')}` : Object.fromEntries(STATUTS.map(([k, l]) => [k, l]))[statut(r)]);
const PROFILS = [['culte', 'Lieu de culte ou bâtiment religieux'], ['associatif', 'Salle des fêtes, polyvalente ou associative'],
                 ['salle', 'Salle recevant du public'], ['transformable', 'Local à transformer']];
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

    const nArch = data.rows.filter(r => r.archive).length;
    // Le bandeau peut être suivi de « Dernière veille : … » quand annonces.json contient le bloc `veille`.
    const bandeau = `Données relevées le ${data.date} (${data.rows.length - nArch} annonces actives${nArch ? `, ${nArch} archivées` : ''}).`;
    const snap = (await page.textContent('#snap')).trim();
    verifier('bandeau', snap.startsWith(bandeau) ? bandeau : snap, bandeau);
    if (data.veille) verifier('bandeau : dernière veille', snap.includes(`Dernière veille : ${data.veille.date}`), true);
    verifier('titre de la page', await page.title(), 'Radar ERP — Île-de-France');
    verifier('titre principal', (await page.textContent('h1')).trim(), 'Radar ERP — Île-de-France');
    verifier('annonces affichées (filtres par défaut)', await compte(), parDefaut.length);
    verifier('fiches affichées (filtres par défaut)', await page.locator('#list article.card').count(), parDefaut.length);

    await page.fill('#bMin', '0');
    await page.fill('#bMax', '999999999');
    await page.$eval('#sMin', e => { e.value = 0; e.dispatchEvent(new Event('input', { bubbles: true })); });
    verifier('annonces sans limite de budget ni de surface', await compte(), visibles.length);
    verifier('étiquettes « Nouveau »', await page.locator('.tag.new').count(), visibles.filter(r => r.nouveau).length);

    // ---- Filtre « Type d'ERP » (tous types) : déclaré ou potentiel, case « déclaré uniquement », « Type non précisé » ----
    const decl = r => { const d = [...(r.typesDeclares || [])]; if ((r.erp === 'V' || r.erp === 'L') && !d.includes(r.erp)) d.push(r.erp); return d; };
    const potl = r => (r.typesPotentiels || []).filter(t => !decl(r).includes(t));
    verifier('types d\'ERP présents sur chaque annonce', data.rows.filter(r => !Array.isArray(r.typesDeclares) || !Array.isArray(r.typesPotentiels)).length, 0);
    verifier('puces « Type d\'ERP » (14 types + non précisé)', await page.locator('#typeChips button').count(), 15);
    for (const t of ['L', 'V', 'M', 'N', 'R', 'U', 'W', 'X']) {
      await page.locator(`#typeChips button[data-k="${t}"]`).click();
      verifier(`filtre type ${t} (déclaré ou potentiel)`, await compte(), visibles.filter(r => decl(r).includes(t) || potl(r).includes(t)).length);
      await page.check('#typesConfirmed');
      verifier(`filtre type ${t} déclaré uniquement`, await compte(), visibles.filter(r => decl(r).includes(t)).length);
      verifier(`pastilles « ${t} » déclarées sur chaque fiche`, await page.locator('#list article.card .tag.t-dec', { hasText: new RegExp(`^${t}`) }).count(), visibles.filter(r => decl(r).includes(t)).length);
      await page.uncheck('#typesConfirmed');
      await page.locator(`#typeChips button[data-k="${t}"]`).click();
    }
    await page.locator('#typeChips button[data-k="M"]').click();
    await page.locator('#typeChips button[data-k="N"]').click();
    verifier('filtre types M + N (union)', await compte(), visibles.filter(r => ['M', 'N'].some(t => decl(r).includes(t) || potl(r).includes(t))).length);
    await page.click('#typesClear');
    verifier('bouton « Tous » (types)', await compte(), visibles.length);
    await page.locator('#typeChips button[data-k="NP"]').click();
    verifier('filtre « Type non précisé »', await compte(), visibles.filter(r => !decl(r).length && !potl(r).length).length);
    await page.click('#typesClear');
    verifier('légende des types', await page.locator('#legend li').count(), 14);

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
    for (const [cle, libelle, cls] of STATUTS) {
      await puce('erpChips', libelle).click();
      verifier(`filtre classement ERP « ${libelle} »`, await compte(), visibles.filter(r => statut(r) === cle).length);
      // Chaque fiche du filtre affiche l'étiquette exacte de son statut.
      verifier(`étiquette « ${libelle} » affichée sur chaque fiche`,
        await page.locator(`#list article.card .tag.${cls}`).filter({ hasText: cle === 'declare' ? /^ERP déclaré : type / : new RegExp(`^${libelle}$`) }).count(), visibles.filter(r => statut(r) === cle).length);
      verifier(`indicateur « type V confirmé » (filtre ${libelle})`, Number((await page.textContent('#kV')).trim()), cle === 'V' ? visibles.filter(r => r.erp === 'V').length : 0);
      await puce('erpChips', libelle).click();
    }
    verifier('statuts ERP des données reconnus', data.rows.filter(r => !['V', 'L', 'verifier'].includes(r.erp)).length, 0);
    verifier('« V » et « L » toujours justifiés', data.rows.filter(r => ['V', 'L'].includes(r.erp) && !r.erpSource).length, 0);
    for (const [cle, libelle] of PROFILS) {
      await puce('profilChips', libelle).click();
      verifier(`filtre profil « ${libelle} »`, await compte(), visibles.filter(r => (r.profil || 'transformable') === cle).length);
      verifier(`indicateur « lieux de culte » (profil ${cle})`, Number((await page.textContent('#kCulte')).trim()), cle === 'culte' ? visibles.filter(r => r.profil === 'culte').length : 0);
      await puce('profilChips', libelle).click();
    }
    verifier('profils des données reconnus', data.rows.filter(r => !PROFILS.some(([k]) => k === r.profil)).length, 0);
    // Annonces archivées : masquées par défaut, visibles avec leur motif quand la case est cochée.
    verifier('archivées masquées par défaut', await page.locator('#list article.card.arch').count(), 0);
    await page.check('#showArchived');
    verifier('case « archivées » : toutes les annonces', await compte(), nonVendues.length);
    verifier('case « archivées » : étiquette sur chaque archivée', await page.locator('#list article.card.arch .tag.arch').count(), archivees.length);
    verifier('case « archivées » : motif affiché', await page.locator('#list article.card.arch .note.hist', { hasText: 'Archivée le' }).count(), archivees.length);
    await page.uncheck('#showArchived');
    verifier('case « archivées » décochée', await compte(), visibles.length);
    verifier('lecture type V affichée sur chaque fiche', await page.locator('#list article.card .note', { hasText: 'Lecture lieu de culte (type V)' }).count(), visibles.filter(r => r.analyseV).length);
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
    verifier('légende de la carte (classement ERP)', (await page.$$eval('.maplegend span', ls => ls.map(l => l.textContent.trim()))).join(' | '),
      'ERP déclaré (type confirmé) | Type V confirmé | ERP à vérifier');
    verifier('attribution OpenStreetMap affichée', (await page.locator('.leaflet-control-attribution').textContent()).includes('OpenStreetMap'), true);

    // Synchronisation avec chaque famille de filtres : le nombre de repères suit toujours le nombre d'annonces affichées.
    const synchro = async nom => verifier(`carte synchronisée : ${nom}`, await marqueurs(), await compte());
    await puce('deptChips', '94').click(); await synchro('département 94');
    verifier('  … attendu (département 94)', await marqueurs(), parDefaut.filter(r => r.dept === '94').length);
    await puce('deptChips', '94').click();
    await puce('erpChips', 'ERP à vérifier').click(); await synchro('classement ERP à vérifier');
    verifier('  … attendu (ERP à vérifier)', await marqueurs(), parDefaut.filter(r => statut(r) === 'verifier').length);
    await puce('erpChips', 'ERP à vérifier').click();
    await puce('profilChips', 'Lieu de culte ou bâtiment religieux').click(); await synchro('profil lieu de culte');
    verifier('  … attendu (lieux de culte)', await marqueurs(), parDefaut.filter(r => r.profil === 'culte').length);
    await puce('profilChips', 'Lieu de culte ou bâtiment religieux').click();
    await page.check('#showArchived'); await synchro('annonces archivées affichées');
    await page.uncheck('#showArchived');
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
      const libelle = etiquette(ligne);
      verifier('fiche : profil du bien', texte.includes(Object.fromEntries(PROFILS)[ligne.profil]), true);
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
    verifier('mobile : lien « Voir les annonces » visible', await mobile.locator('a.tolist').isVisible(), true);

    // ---- Audit du 14/11/2026 : nature de la vente, annonces masquées, anciens réglages, échec d'actualisation ----
    const NATURES = { vente: 'Vente des murs', murs_occupes: 'Murs vendus occupés (bail en cours)', murs_et_fonds: 'Murs et fonds de commerce',
      fonds: 'Fonds de commerce ou droit au bail seul', vente_ou_location: 'Vente ou location : à confirmer' };
    const audit = await (await navigateur.newContext()).newPage();
    await audit.context().route('**/tile.openstreetmap.org/**', r => r.abort());
    await audit.goto(`http://127.0.0.1:${port}/index.html`); await audit.waitForTimeout(500);
    const cpt = async () => Number((await audit.textContent('#kCount')).trim());
    verifier('nature de la vente renseignée sur chaque annonce', data.rows.filter(r => !(r.nature in NATURES)).length, 0);
    for (const [cle, libelle] of Object.entries(NATURES)) {
      await audit.locator('#natureChips button', { hasText: libelle }).first().click();
      verifier(`filtre nature « ${libelle} »`, await cpt(), parDefaut.filter(r => r.nature === cle).length);
      await audit.locator('#natureChips button', { hasText: libelle }).first().click();
    }
    verifier('étiquette de nature sur les fiches (hors vente simple)', await audit.locator('#list article.card .tag.chk', { hasText: /occupés|fonds|à confirmer/ }).count(),
      parDefaut.filter(r => r.nature && r.nature !== 'vente').length);
    const masquees = visibles.length - parDefaut.length;
    verifier('bandeau : annonces masquées par les filtres par défaut', masquees > 0 ? (await audit.textContent('#masque')).includes(`${masquees} annonce`) : await audit.locator('#masque').isHidden(), true);
    await audit.click('#toutAfficher');
    verifier('« Tout afficher » : toutes les annonces actives', await cpt(), visibles.length);
    verifier('« Tout afficher » : bandeau masqué', await audit.locator('#masque').isHidden(), true);
    await audit.click('#resetBtn');
    // Ancien réglage enregistré (budget 300-600 k€ de l'ancien tableau de bord et type V) : signalé, et « Tout afficher » le lève.
    await audit.evaluate(() => localStorage.setItem('erpAll.filters', JSON.stringify({ bMin: 300000, bMax: 600000, types: ['V'] })));
    await audit.reload(); await audit.waitForTimeout(500);
    verifier('ancien réglage enregistré signalé', (await audit.textContent('#masque')).includes('visite précédente'), true);
    await audit.click('#toutAfficher');
    verifier('ancien réglage levé par « Tout afficher »', await cpt(), visibles.length);
    await audit.evaluate(() => localStorage.clear());
    // Échec de l'actualisation : signalé dans le bandeau de fraîcheur, les données publiées avec la page restent affichées.
    const panne = await (await navigateur.newContext()).newPage();
    await panne.context().route('**/annonces.json*', r => r.fulfill({ status: 503, body: '' }));
    await panne.goto(`http://127.0.0.1:${port}/index.html`); await panne.waitForTimeout(600);
    verifier('échec d\'actualisation signalé', (await panne.textContent('#snap')).includes('Actualisation impossible'), true);
    verifier('échec d\'actualisation : annonces toujours affichées', Number((await panne.textContent('#kCount')).trim()), parDefaut.length);
    // Date de dernière veille (champ facultatif « veille » écrit par la routine).
    const veille = await (await navigateur.newContext()).newPage();
    await veille.context().route('**/annonces.json*', r => r.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify(Object.assign({}, data, { veille: { date: '14/11/2026', statut: 'ok', ajouts: 0 } })) }));
    await veille.goto(`http://127.0.0.1:${port}/index.html`); await veille.waitForTimeout(600);
    verifier('date de dernière veille affichée (aucune nouvelle annonce)', (await veille.textContent('#snap')).includes('Dernière veille : 14/11/2026 — 0 nouvelle annonce'), true);

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

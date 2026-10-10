import { formatCount, formatPercent } from './format';
import type { ResultRow } from './leader';
import type { TerritoryResult } from './types';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const ACCENT = '#db4c3f';
const MUTED = '#777777';
const TEXT = '#202020';
const SEA = '#d3dde8';
const SITE = 'https://charlescoiffier.github.io/oripol/';
const SOURCE = 'Données : ministère de l’Intérieur (data.gouv.fr), Insee, IGN';

export interface Legend {
	/** Échelle continue (mode évolution) ou pastilles de familles (mode classique). */
	gradient?: { left: string; middle: string; right: string; leftLabel: string; rightLabel: string };
	swatches?: { label: string; color: string }[];
	noData: { label: string; color: string };
}

export interface ExportInput {
	title: string;
	subtitle: string;
	map: HTMLCanvasElement | null;
	legend: Legend;
	/** Blocs de graphiques ou de tableaux déjà dessinés (largeur 1000 px). */
	blocks: HTMLCanvasElement[];
	/** Carte et légende incluses (par défaut oui). */
	showMap?: boolean;
}

export const BLOCK_WIDTH = 1000;
export const A4 = { width: 1654, height: 2339 }; // 200 dpi
const PNG_WIDTH = 1600;
const MARGIN = 56;
const GAP = 32;

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
	const c = document.createElement('canvas');
	c.width = Math.round(w);
	c.height = Math.round(h);
	const ctx = c.getContext('2d') as CanvasRenderingContext2D;
	ctx.fillStyle = '#ffffff';
	ctx.fillRect(0, 0, c.width, c.height);
	return [c, ctx];
}

/** Texte tronqué avec « … » pour tenir dans `max` pixels. */
function fit(ctx: CanvasRenderingContext2D, text: string, max: number): string {
	if (ctx.measureText(text).width <= max) return text;
	let t = text;
	while (t.length > 1 && ctx.measureText(`${t}…`).width > max) t = t.slice(0, -1);
	return `${t}…`;
}

function loadImage(src: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error('Image illisible'));
		img.src = src;
	});
}

function heading(ctx: CanvasRenderingContext2D, text: string, y: number): number {
	ctx.fillStyle = MUTED;
	ctx.font = `600 24px ${FONT}`;
	ctx.textBaseline = 'top';
	ctx.fillText(text.toUpperCase(), 0, y);
	return y + 40;
}

/** Bloc « graphique » : titre, image du graphique et pastilles de légende éventuelles. */
export async function imageBlock(
	title: string,
	dataUrl: string,
	legend: { label: string; color: string; dashed?: boolean }[] = [],
	/** « ← Gauche / Droite → » sous le graphique ; `cssWidth` : largeur du graphique à l'écran (pour caler les marges). */
	sides?: { cssWidth: number }
): Promise<HTMLCanvasElement> {
	const img = await loadImage(dataUrl);
	const h = Math.round((img.height / img.width) * BLOCK_WIDTH);
	const measure = canvas(BLOCK_WIDTH, 10)[1];
	measure.font = `22px ${FONT}`;
	// pastilles de légende : retour à la ligne quand la ligne est pleine
	let x = 0;
	let lines = 1;
	for (const l of legend) {
		const w = measure.measureText(l.label).width + 46;
		if (x + w > BLOCK_WIDTH) {
			x = 0;
			lines += 1;
		}
		x += w;
	}
	const sidesH = sides ? 34 : 0;
	const [c, ctx] = canvas(BLOCK_WIDTH, 40 + h + sidesH + (legend.length ? 12 + lines * 34 : 0));
	let y = heading(ctx, title, 0);
	ctx.drawImage(img, 0, y, BLOCK_WIDTH, h);
	y += h;
	if (sides) {
		// mêmes marges que dans le panneau (40 px à gauche, 14 px à droite)
		const k = BLOCK_WIDTH / sides.cssWidth;
		ctx.font = `22px ${FONT}`;
		ctx.textBaseline = 'middle';
		ctx.fillStyle = MUTED;
		ctx.textAlign = 'left';
		ctx.fillText('← Gauche', 40 * k, y + 16);
		ctx.textAlign = 'right';
		ctx.fillText('Droite →', BLOCK_WIDTH - 14 * k, y + 16);
		ctx.textAlign = 'left';
		y += sidesH;
	}
	y += 12;
	ctx.font = `22px ${FONT}`;
	ctx.textBaseline = 'middle';
	x = 0;
	let row = 0;
	for (const l of legend) {
		const w = ctx.measureText(l.label).width + 46;
		if (x + w > BLOCK_WIDTH) {
			x = 0;
			row += 1;
		}
		const cy = y + row * 34 + 14;
		if (l.dashed) {
			ctx.strokeStyle = l.color;
			ctx.lineWidth = 3;
			ctx.setLineDash([6, 4]);
			ctx.beginPath();
			ctx.moveTo(x, cy);
			ctx.lineTo(x + 22, cy);
			ctx.stroke();
			ctx.setLineDash([]);
		} else {
			ctx.fillStyle = l.color;
			ctx.fillRect(x, cy - 9, 18, 18);
		}
		ctx.fillStyle = TEXT;
		ctx.fillText(l.label, x + 30, cy);
		x += w;
	}
	return c;
}

const MAX_ROWS = 14;

/** Bloc « résultats » (mode classique) : listes, voix, pourcentages et participation. */
export function resultsBlock(
	electionLabel: string,
	result: TerritoryResult,
	rows: ResultRow[],
	colorOf: (family: string | undefined) => string
): HTMLCanvasElement {
	const shown = rows.slice(0, MAX_ROWS);
	const rest = rows.slice(MAX_ROWS);
	const lines = shown.length + (rest.length ? 1 : 0);
	const abstentions = Math.max(0, result.inscrits - result.votants);
	const pct = (n: number) => (result.inscrits > 0 ? ` (${formatPercent(n / result.inscrits)})` : '');
	const merged = result.blancs === 0 && result.nuls > 0;
	const turnout: [string, string][] = [
		['Inscrits', formatCount(result.inscrits)],
		['Abstentions', `${formatCount(abstentions)}${pct(abstentions)}`],
		['Votants', `${formatCount(result.votants)}${pct(result.votants)}`],
		...(merged
			? ([['Blancs et nuls', `${formatCount(result.nuls)}${pct(result.nuls)}`]] as [string, string][])
			: ([
					['Blancs', `${formatCount(result.blancs)}${pct(result.blancs)}`],
					['Nuls', `${formatCount(result.nuls)}${pct(result.nuls)}`]
				] as [string, string][])),
		['Exprimés', formatCount(result.exprimes)]
	];
	const [c, ctx] = canvas(BLOCK_WIDTH, 40 + 34 + 12 + lines * 40 + 24 + turnout.length * 34 + 8);
	let y = heading(ctx, 'Résultats', 0);
	ctx.textBaseline = 'middle';
	ctx.fillStyle = MUTED;
	ctx.font = `22px ${FONT}`;
	ctx.fillText(electionLabel, 0, y + 8);
	ctx.textAlign = 'right';
	ctx.fillText('Voix', BLOCK_WIDTH - 170, y + 8);
	ctx.fillText('% exprimés', BLOCK_WIDTH, y + 8);
	ctx.textAlign = 'left';
	y += 34 + 12;
	const maxShare = Math.max(0.01, ...rows.map((r) => r.share));
	const draw = (label: string, color: string, voix: number, share: number) => {
		ctx.fillStyle = color;
		ctx.fillRect(0, y + 8, 18, 18);
		ctx.fillStyle = TEXT;
		ctx.font = `24px ${FONT}`;
		ctx.fillText(fit(ctx, label, 560), 32, y + 18);
		ctx.fillStyle = color;
		ctx.globalAlpha = 0.75;
		ctx.fillRect(32, y + 34, Math.max(2, (share / maxShare) * 540), 4);
		ctx.globalAlpha = 1;
		ctx.fillStyle = TEXT;
		ctx.textAlign = 'right';
		ctx.fillText(formatCount(voix), BLOCK_WIDTH - 170, y + 18);
		ctx.fillText(formatPercent(share), BLOCK_WIDTH, y + 18);
		ctx.textAlign = 'left';
		y += 40;
	};
	for (const r of shown) draw(r.person ? `${r.person} · ${r.label}` : r.label, colorOf(r.family), r.voix, r.share);
	if (rest.length) {
		draw(
			`Autres (${rest.length} listes)`,
			'#c9c9c9',
			rest.reduce((s, r) => s + r.voix, 0),
			rest.reduce((s, r) => s + r.share, 0)
		);
	}
	y += 24;
	ctx.font = `24px ${FONT}`;
	for (const [label, value] of turnout) {
		ctx.fillStyle = MUTED;
		ctx.textAlign = 'left';
		ctx.fillText(label, 0, y + 14);
		ctx.fillStyle = TEXT;
		ctx.textAlign = 'right';
		ctx.fillText(value, BLOCK_WIDTH, y + 14);
		y += 34;
	}
	ctx.textAlign = 'left';
	return c;
}

function drawHeader(ctx: CanvasRenderingContext2D, w: number, input: ExportInput): number {
	ctx.textBaseline = 'top';
	ctx.fillStyle = ACCENT;
	ctx.font = `700 30px ${FONT}`;
	ctx.fillText('Oripol', MARGIN, MARGIN);
	ctx.fillStyle = TEXT;
	ctx.font = `700 52px ${FONT}`;
	ctx.fillText(fit(ctx, input.title, w - 2 * MARGIN), MARGIN, MARGIN + 46);
	ctx.fillStyle = MUTED;
	ctx.font = `32px ${FONT}`;
	ctx.fillText(fit(ctx, input.subtitle, w - 2 * MARGIN), MARGIN, MARGIN + 114);
	return MARGIN + 114 + 56;
}

function drawMap(ctx: CanvasRenderingContext2D, map: HTMLCanvasElement | null, x: number, y: number, w: number, h: number) {
	ctx.fillStyle = SEA;
	ctx.fillRect(x, y, w, h);
	if (map) {
		// l'image est entièrement visible, centrée dans le cadre
		const k = Math.min(w / map.width, h / map.height);
		const dw = map.width * k;
		const dh = map.height * k;
		ctx.drawImage(map, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
	}
	ctx.strokeStyle = '#c9d3de';
	ctx.lineWidth = 2;
	ctx.strokeRect(x, y, w, h);
}

const LEGEND_HEIGHT = 96;

function drawLegend(ctx: CanvasRenderingContext2D, legend: Legend, x: number, y: number, w: number) {
	ctx.textBaseline = 'middle';
	ctx.font = `24px ${FONT}`;
	let cx = x;
	const cy = y + 26;
	if (legend.gradient) {
		const g = legend.gradient;
		const barW = 460;
		const grad = ctx.createLinearGradient(x, 0, x + barW, 0);
		grad.addColorStop(0, g.left);
		grad.addColorStop(0.5, g.middle);
		grad.addColorStop(1, g.right);
		ctx.fillStyle = grad;
		ctx.fillRect(x, y + 6, barW, 22);
		ctx.strokeStyle = '#e2e2e2';
		ctx.strokeRect(x, y + 6, barW, 22);
		ctx.fillStyle = MUTED;
		ctx.fillText(g.leftLabel, x, y + 52);
		ctx.textAlign = 'right';
		ctx.fillText(g.rightLabel, x + barW, y + 52);
		ctx.textAlign = 'left';
		cx = x + barW + 48;
		ctx.fillStyle = legend.noData.color;
		ctx.fillRect(cx, cy - 11, 22, 22);
		ctx.fillStyle = TEXT;
		ctx.fillText(legend.noData.label, cx + 34, cy);
		return;
	}
	let row = 0;
	for (const s of [...(legend.swatches ?? []), legend.noData]) {
		const sw = ctx.measureText(s.label).width + 64;
		if (cx + sw > x + w) {
			cx = x;
			row += 1;
		}
		const yy = cy + row * 38;
		ctx.fillStyle = s.color;
		ctx.fillRect(cx, yy - 11, 22, 22);
		ctx.fillStyle = TEXT;
		ctx.fillText(s.label, cx + 34, yy);
		cx += sw;
	}
}

function drawFooter(ctx: CanvasRenderingContext2D, w: number, h: number) {
	ctx.textBaseline = 'alphabetic';
	ctx.fillStyle = MUTED;
	ctx.font = `20px ${FONT}`;
	ctx.fillText(`${SITE} · ${SOURCE}`, MARGIN, h - MARGIN + 18);
	ctx.textAlign = 'right';
	ctx.fillText(new Date().toLocaleDateString('fr-FR'), w - MARGIN, h - MARGIN + 18);
	ctx.textAlign = 'left';
}

/** Hauteur de la légende : plusieurs lignes de pastilles en mode classique. */
function legendHeight(legend: Legend, w: number): number {
	if (legend.gradient) return LEGEND_HEIGHT;
	const [, m] = canvas(10, 10);
	m.font = `24px ${FONT}`;
	let x = 0;
	let rows = 1;
	for (const s of [...(legend.swatches ?? []), legend.noData]) {
		const sw = m.measureText(s.label).width + 64;
		if (x + sw > w) {
			x = 0;
			rows += 1;
		}
		x += sw;
	}
	return 26 + rows * 38 + 20;
}

/** Mise en page : titre, carte, légende, puis graphiques côte à côte. `fixedHeight` impose la hauteur (page A4). */
export function compose(input: ExportInput, width: number, fixedHeight?: number): HTMLCanvasElement {
	const showMap = input.showMap !== false;
	const inner = width - 2 * MARGIN;
	const n = input.blocks.length;
	const cellW = n === 0 ? 0 : Math.min(n === 1 ? 820 : inner, (inner - (n - 1) * GAP) / n);
	const legendH = showMap ? legendHeight(input.legend, inner) : 0;
	const FOOTER = 60;
	const headerH = MARGIN + 114 + 56;
	const naturalBlocksH = Math.max(0, ...input.blocks.map((b) => (b.height * cellW) / b.width));
	let blocksH = naturalBlocksH;
	let mapH = showMap ? 900 : 0;
	let k = 1;
	let height: number;
	if (fixedHeight) {
		height = fixedHeight;
		const room = (bh: number) => height - headerH - legendH - bh - (n ? 2 * GAP : GAP) - FOOTER - MARGIN;
		// on réduit les graphiques tant que la carte resterait trop petite
		while (room(naturalBlocksH * k) < 700 && k > 0.4) k -= 0.05;
		blocksH = naturalBlocksH * k;
		mapH = Math.max(300, room(blocksH));
	} else {
		height = headerH + (showMap ? mapH + GAP + legendH : 0) + (n ? (showMap ? GAP : 0) + blocksH : 0) + FOOTER + MARGIN;
	}

	const [c, ctx] = canvas(width, height);
	let y = drawHeader(ctx, width, input);
	if (showMap) {
		drawMap(ctx, input.map, MARGIN, y, inner, mapH);
		y += mapH + GAP;
		drawLegend(ctx, input.legend, MARGIN, y, inner);
		y += legendH + GAP;
	}
	const w = cellW * k;
	const used = n * w + (n - 1) * GAP;
	let x = MARGIN + (inner - used) / 2;
	for (const b of input.blocks) {
		ctx.drawImage(b, x, y, w, (b.height * w) / b.width);
		x += w + GAP;
	}
	drawFooter(ctx, width, height);
	return c;
}

export const composePng = (input: ExportInput) => compose(input, PNG_WIDTH);
export const composeA4 = (input: ExportInput) => compose(input, A4.width, A4.height);

function download(url: string, filename: string) {
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.append(a);
	a.click();
	a.remove();
}

export function savePng(c: HTMLCanvasElement, filename: string) {
	download(c.toDataURL('image/png'), filename);
}

/** Page A4 portrait unique contenant l'image composée. */
export async function savePdf(c: HTMLCanvasElement, filename: string) {
	const { jsPDF } = await import('jspdf');
	const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
	pdf.addImage(c.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, 210, 297);
	pdf.save(filename);
}

/** Nom de fichier sûr : « oripol-presidentielles-2022-1er-tour-maine-et-loire ». */
export function fileName(...parts: string[]): string {
	return (
		['oripol', ...parts]
			.join('-')
			.normalize('NFD')
			.replace(/[̀-ͯ]/g, '')
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-|-$/g, '') || 'oripol'
	);
}

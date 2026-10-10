import type { Classification, FamilyId, Level } from './types';
import type { PaletteId } from './palette';
import type { AppState, Mode } from './url-state';

class AppStore {
	election = $state<string | null>(null);
	territory = $state<string | null>(null);
	level = $state<Level>('departements');
	mode = $state<Mode>('evolution');
	palette = $state<PaletteId>('standard');
	classification = $state<Classification>({ positions: {}, listFamilies: {} });

	snapshot(): AppState {
		return {
			election: this.election,
			territory: this.territory,
			level: this.level,
			mode: this.mode,
			palette: this.palette,
			classification: $state.snapshot(this.classification) as Classification
		};
	}

	hydrate(s: AppState) {
		this.election = s.election;
		this.territory = s.territory;
		this.level = s.level;
		this.mode = s.mode;
		this.palette = s.palette;
		this.classification = s.classification;
	}

	setPosition(family: FamilyId, value: number | null) {
		this.classification.positions = { ...this.classification.positions, [family]: value };
	}

	setListFamily(listId: string, family: FamilyId | null) {
		const next = { ...this.classification.listFamilies };
		if (family === null) delete next[listId];
		else next[listId] = family;
		this.classification.listFamilies = next;
	}

	resetClassification() {
		this.classification = { positions: {}, listFamilies: {} };
	}
}

export const app = new AppStore();

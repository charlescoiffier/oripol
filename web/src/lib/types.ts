export type FamilyId =
	| 'extreme_gauche'
	| 'gauche'
	| 'centre'
	| 'droite'
	| 'extreme_droite'
	| 'divers'
	| 'regionaliste';

export type Precision = 'commune' | 'circonscription' | 'canton' | 'departement';
export type Level = 'regions' | 'departements' | 'communes';

export interface Family {
	id: FamilyId;
	label: string;
	position: number | null;
	color: string;
}

export interface ListInfo {
	label: string;
	family: FamilyId;
}

export interface TerritoryResult {
	inscrits: number;
	votants: number;
	blancs: number;
	nuls: number;
	exprimes: number;
	voix: Record<string, number>;
	precision: Precision;
}

export interface Classification {
	positions: Partial<Record<FamilyId, number | null>>;
	listFamilies: Record<string, FamilyId>;
}

export interface ElectionData {
	id: string;
	type: string;
	year: number;
	round: number;
	label: string;
	lists: Record<string, ListInfo>;
	territories: Record<string, TerritoryResult>;
}

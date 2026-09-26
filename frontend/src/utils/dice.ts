/**
 * Client-side dice arithmetic engine and formula parser.
 * Mirrors backend calculation logic for zero-latency UI interactions.
 */

export interface DiceRollResult {
  formula: string;
  count: number;
  sides: number;
  modifier: number;
  keepHighest?: number;
  keepLowest?: number;
  rolls: number[];
  keptRolls: number[];
  total: number;
  isCrit: boolean;
  isFumble: boolean;
}

export const DICE_FORMULA_REGEX =
  /^\s*(\d+)?d(\d+)\s*(?:(kh|kl)\s*(\d+))?\s*(?:([+-])\s*(\d+))?\s*$/i;

/**
 * Evaluates a roll of dice with sides and optional keep rules.
 */
export function evaluateDice(
  count: number,
  sides: number,
  modifier = 0,
  keepHighest?: number,
  keepLowest?: number,
  fixedRolls?: number[]
): DiceRollResult {
  if (count < 1) {
    throw new Error(`Dice count must be at least 1, got ${count}`);
  }
  if (sides < 1) {
    throw new Error(`Dice sides must be at least 1, got ${sides}`);
  }
  if (keepHighest !== undefined && keepLowest !== undefined) {
    throw new Error('Cannot specify both keepHighest and keepLowest');
  }

  const rolls: number[] =
    fixedRolls !== undefined
      ? [...fixedRolls]
      : Array.from({ length: count }, () => Math.floor(Math.random() * sides) + 1);

  let keptRolls: number[];
  if (keepHighest !== undefined && keepHighest !== null) {
    const sorted = [...rolls].sort((a, b) => b - a);
    keptRolls = sorted.slice(0, keepHighest);
  } else if (keepLowest !== undefined && keepLowest !== null) {
    const sorted = [...rolls].sort((a, b) => a - b);
    keptRolls = sorted.slice(0, keepLowest);
  } else {
    keptRolls = [...rolls];
  }

  const total = keptRolls.reduce((sum, val) => sum + val, 0) + modifier;

  let isCrit = false;
  let isFumble = false;
  if (sides === 20) {
    if (keptRolls.includes(20)) {
      isCrit = true;
    } else if (keptRolls.includes(1)) {
      isFumble = true;
    }
  }

  return {
    formula: '',
    count,
    sides,
    modifier,
    keepHighest,
    keepLowest,
    rolls,
    keptRolls,
    total,
    isCrit,
    isFumble,
  };
}

/**
 * Parses standard TTRPG dice notation and evaluates the roll.
 * Supports expressions such as 1d20+5, 2d20kh1+3 (advantage), 2d20kl1+3 (disadvantage),
 * 8d6+4, 4d6kh3, d20+2.
 */
export function parseAndRoll(formula: string, fixedRolls?: number[]): DiceRollResult {
  const match = formula.trim().match(DICE_FORMULA_REGEX);
  if (!match) {
    throw new Error(`Invalid dice formula: ${formula}`);
  }

  const count = match[1] ? parseInt(match[1], 10) : 1;
  const sides = parseInt(match[2], 10);
  const keepMode = match[3]?.toLowerCase();
  const keepVal = match[4] ? parseInt(match[4], 10) : undefined;

  const keepHighest = keepMode === 'kh' ? keepVal : undefined;
  const keepLowest = keepMode === 'kl' ? keepVal : undefined;

  const sign = match[5];
  const modVal = match[6] ? parseInt(match[6], 10) : 0;
  const modifier = sign === '-' ? -modVal : modVal;

  const result = evaluateDice(count, sides, modifier, keepHighest, keepLowest, fixedRolls);
  result.formula = formula.trim();
  return result;
}

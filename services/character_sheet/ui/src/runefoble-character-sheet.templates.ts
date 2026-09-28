/**
 * Character Sheet Templates Aggregator Facade.
 *
 * Governed by ADR-0004, ADR-0012, and ADR-0013.
 * Modular sub-templates decomposed under ./templates/.
 */

export {
  renderSheetHeader,
  renderVitalsGrid,
} from './templates/stats.template.ts';

export {
  renderEquipmentAndInventory,
} from './templates/inventory.template.ts';

export {
  renderConditionsPanel,
} from './templates/conditions.template.ts';

export {
  renderSpellbookPanel,
} from './templates/spells.template.ts';

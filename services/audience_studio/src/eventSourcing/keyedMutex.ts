/**
 * Serializes work per key inside this process. Commands on one stream run one at a time,
 * so the optimistic version check in the store is never the first line of defence.
 */

export class KeyedMutex {
  private readonly tails = new Map<string, Promise<void>>();

  async run<T>(keys: string[], work: () => Promise<T>): Promise<T> {
    // Acquire keys in sorted order, so two multi-key callers cannot deadlock.
    const ordered = [...new Set(keys)].sort();
    const releases: Array<() => void> = [];
    try {
      for (const key of ordered) {
        const previous = this.tails.get(key) ?? Promise.resolve();
        let release!: () => void;
        const gate = new Promise<void>((resolve) => {
          release = resolve;
        });
        const tail = previous.then(() => gate);
        this.tails.set(key, tail);
        await previous;
        releases.push(() => {
          release();
          if (this.tails.get(key) === tail) this.tails.delete(key);
        });
      }
      return await work();
    } finally {
      for (const release of releases.reverse()) release();
    }
  }
}

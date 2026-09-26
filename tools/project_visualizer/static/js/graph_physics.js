// --- Runefoble Project Content Visualizer: Graph Physics & Layout Engine ---
(function() {
  window.visualizer = window.visualizer || {};

  class ForceSimulation {
    constructor(nodes, edges, options = {}) {
      this.nodes = nodes;
      this.edges = edges;
      this.width = options.width || 1200;
      this.height = options.height || 800;
      this.centerX = this.width / 2;
      this.centerY = this.height / 2;

      this.springLength = options.springLength || 120;
      this.springStrength = options.springStrength || 0.035;
      this.repulsion = options.repulsion || 3800;
      this.centering = options.centering || 0.012;
      this.damping = options.damping || 0.86;

      this.alpha = 1.0;
      this.alphaDecay = 0.008;
      this.alphaMin = 0.005;
      this.isRunning = false;
      this.animId = null;
      this.onTick = null;

      this.initNodes();
    }

    initNodes() {
      const nodeMap = new Map();
      this.nodes.forEach((n, i) => {
        if (n.x === undefined) {
          const angle = (i / Math.max(this.nodes.length, 1)) * 2 * Math.PI;
          const radius = 150 + (i % 5) * 40;
          n.x = this.centerX + Math.cos(angle) * radius;
          n.y = this.centerY + Math.sin(angle) * radius;
        }
        n.vx = 0;
        n.vy = 0;
        nodeMap.set(n.id, n);
      });

      this.edgePairs = [];
      this.edges.forEach(e => {
        const s = nodeMap.get(e.source_id);
        const t = nodeMap.get(e.target_id);
        if (s && t) {
          this.edgePairs.push({ source: s, target: t, relation: e.relation });
        }
      });
    }

    step() {
      if (this.alpha < this.alphaMin) {
        this.stop();
        return;
      }

      const nodes = this.nodes;
      const nLen = nodes.length;

      // 1. Repulsion between all node pairs (Coulomb's Law with cutoff)
      for (let i = 0; i < nLen; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nLen; j++) {
          const n2 = nodes[j];
          let dx = n1.x - n2.x;
          let dy = n1.y - n2.y;
          let distSq = dx * dx + dy * dy;
          if (distSq < 1) distSq = 1;
          const dist = Math.sqrt(distSq);

          if (dist < 450) {
            const force = (this.repulsion / distSq) * this.alpha;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (!n1.isFixed) { n1.vx += fx; n1.vy += fy; }
            if (!n2.isFixed) { n2.vx -= fx; n2.vy -= fy; }
          }
        }
      }

      // 2. Spring Attraction along Edges (Hooke's Law)
      this.edgePairs.forEach(pair => {
        const s = pair.source;
        const t = pair.target;
        let dx = t.x - s.x;
        let dy = t.y - s.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) dist = 1;

        const displacement = dist - this.springLength;
        const force = displacement * this.springStrength * this.alpha;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (!s.isFixed) { s.vx += fx; s.vy += fy; }
        if (!t.isFixed) { t.vx -= fx; t.vy -= fy; }
      });

      // 3. Centering Gravitational Pull
      nodes.forEach(n => {
        if (!n.isFixed) {
          n.vx += (this.centerX - n.x) * this.centering * this.alpha;
          n.vy += (this.centerY - n.y) * this.centering * this.alpha;
        }
      });

      // 4. Update Velocities and Positions with Damping
      nodes.forEach(n => {
        if (!n.isFixed) {
          n.vx *= this.damping;
          n.vy *= this.damping;
          n.x += n.vx;
          n.y += n.vy;

          // Soft boundary clamping
          const pad = 40;
          if (n.x < pad) { n.x = pad; n.vx = 0; }
          if (n.x > this.width - pad) { n.x = this.width - pad; n.vx = 0; }
          if (n.y < pad) { n.y = pad; n.vy = 0; }
          if (n.y > this.height - pad) { n.y = this.height - pad; n.vy = 0; }
        }
      });

      this.alpha *= (1 - this.alphaDecay);
    }

    start(onTick) {
      if (onTick) this.onTick = onTick;
      if (this.isRunning) return;
      this.isRunning = true;

      const loop = () => {
        if (!this.isRunning) return;
        this.step();
        if (this.onTick) this.onTick();
        this.animId = requestAnimationFrame(loop);
      };
      this.animId = requestAnimationFrame(loop);
    }

    stop() {
      this.isRunning = false;
      if (this.animId) {
        cancelAnimationFrame(this.animId);
        this.animId = null;
      }
    }

    reheat(targetAlpha = 0.8) {
      this.alpha = targetAlpha;
      if (!this.isRunning) {
        this.start(this.onTick);
      }
    }

    applyFlowLayout() {
      this.stop();
      const cols = { persona: 100, story: 340, prd: 600, task: 870, adr: 1120 };
      const buckets = { persona: [], story: [], prd: [], task: [], adr: [] };
      this.nodes.forEach(n => {
        if (buckets[n.type]) buckets[n.type].push(n);
      });

      Object.keys(buckets).forEach(type => {
        const arr = buckets[type];
        const step = (this.height - 120) / Math.max(arr.length, 1);
        arr.forEach((n, idx) => {
          n.x = (cols[type] || 600) + (Math.sin(idx * 2) * 12);
          n.y = 70 + idx * step;
          n.vx = 0;
          n.vy = 0;
        });
      });
      if (this.onTick) this.onTick();
    }

    applyRadialLayout() {
      this.stop();
      const ringRadii = { persona: 110, prd: 220, story: 330, task: 450, adr: 560 };
      const buckets = { persona: [], prd: [], story: [], task: [], adr: [] };
      this.nodes.forEach(n => {
        if (buckets[n.type]) buckets[n.type].push(n);
      });

      Object.keys(buckets).forEach(type => {
        const arr = buckets[type];
        const radius = ringRadii[type] || 300;
        arr.forEach((n, i) => {
          const angle = (i / Math.max(arr.length, 1)) * 2 * Math.PI;
          n.x = this.centerX + Math.cos(angle) * radius;
          n.y = this.centerY + Math.sin(angle) * radius;
          n.vx = 0;
          n.vy = 0;
        });
      });
      if (this.onTick) this.onTick();
    }
  }

  window.visualizer.ForceSimulation = ForceSimulation;
})();

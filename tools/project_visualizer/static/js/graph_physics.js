// --- Runefoble Project Content Visualizer: Graph Physics & Layout Engine ---
(function() {
  window.visualizer = window.visualizer || {};

  class ForceSimulation {
    constructor(nodes, edges, options = {}) {
      this.nodes = nodes;
      this.edges = edges;
      this.width = options.width || 2200;
      this.height = options.height || 1400;
      this.centerX = this.width / 2;
      this.centerY = this.height / 2;

      this.springLength = options.springLength || 170;
      this.springStrength = options.springStrength || 0.015;
      this.repulsion = options.repulsion || 7500;
      this.centering = options.centering || 0.006;
      this.damping = options.damping || 0.72;
      this.maxSpeed = options.maxSpeed || 10;

      this.alpha = 1.0;
      this.alphaDecay = 0.016;
      this.alphaMin = 0.003;
      this.isRunning = false;
      this.animId = null;
      this.onTick = null;

      this.initNodes();
    }

    initNodes() {
      const nodeMap = new Map();
      const colX = {
        persona: this.centerX - 720,
        story: this.centerX - 380,
        prd: this.centerX - 40,
        task: this.centerX + 340,
        adr: this.centerX + 720,
      };
      const typeCounts = {};

      this.nodes.forEach(n => {
        typeCounts[n.type] = (typeCounts[n.type] || 0) + 1;
        if (n.x === undefined) {
          const baseCol = colX[n.type] || this.centerX;
          const idx = typeCounts[n.type];
          n.x = baseCol + (Math.sin(idx * 3) * 70);
          n.y = 120 + ((idx * 60) % (this.height - 240));
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

      // 1. Soft-core Coulomb repulsion between all node pairs
      for (let i = 0; i < nLen; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nLen; j++) {
          const n2 = nodes[j];
          const dx = n1.x - n2.x;
          const dy = n1.y - n2.y;
          const distSq = dx * dx + dy * dy;

          if (distSq < 360000) { // 600px cutoff
            const dist = Math.sqrt(distSq) || 1;
            const softDistSq = distSq + 2000; // Soft-core prevents violent repulsion spikes
            const force = (this.repulsion / softDistSq) * this.alpha;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (!n1.isFixed) { n1.vx += fx; n1.vy += fy; }
            if (!n2.isFixed) { n2.vx -= fx; n2.vy -= fy; }
          }
        }
      }

      // 2. Bounded Hooke's Law spring attraction along edges
      this.edgePairs.forEach(pair => {
        const s = pair.source;
        const t = pair.target;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        // Smooth clamp on displacement prevents slingshotting
        const displacement = Math.max(-130, Math.min(130, dist - this.springLength));
        const force = displacement * this.springStrength * this.alpha;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (!s.isFixed) { s.vx += fx; s.vy += fy; }
        if (!t.isFixed) { t.vx -= fx; t.vy -= fy; }
      });

      // 3. Gentle Centering Gravity
      nodes.forEach(n => {
        if (!n.isFixed) {
          n.vx += (this.centerX - n.x) * this.centering * this.alpha;
          n.vy += (this.centerY - n.y) * this.centering * this.alpha;
        }
      });

      // 4. Velocity Clamping, Damping, and Position Integration
      const pad = 60;
      nodes.forEach(n => {
        if (!n.isFixed) {
          const speed = Math.hypot(n.vx, n.vy);
          if (speed > this.maxSpeed) {
            n.vx = (n.vx / speed) * this.maxSpeed;
            n.vy = (n.vy / speed) * this.maxSpeed;
          }
          n.vx *= this.damping;
          n.vy *= this.damping;
          n.x += n.vx;
          n.y += n.vy;

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

    reheat(targetAlpha = 0.7) {
      this.alpha = targetAlpha;
      if (!this.isRunning) {
        this.start(this.onTick);
      }
    }

    applyFlowLayout() {
      this.stop();
      const cols = { persona: 160, story: 560, prd: 1000, task: 1460, adr: 1900 };
      const buckets = { persona: [], story: [], prd: [], task: [], adr: [] };
      this.nodes.forEach(n => {
        if (buckets[n.type]) buckets[n.type].push(n);
      });

      Object.keys(buckets).forEach(type => {
        const arr = buckets[type];
        const step = (this.height - 180) / Math.max(arr.length, 1);
        arr.forEach((n, idx) => {
          n.x = (cols[type] || 1000) + (Math.sin(idx * 2) * 20);
          n.y = 90 + idx * step;
          n.vx = 0;
          n.vy = 0;
        });
      });
      if (this.onTick) this.onTick();
    }

    applyRadialLayout() {
      this.stop();
      const ringRadii = { persona: 180, prd: 360, story: 520, task: 720, adr: 920 };
      const buckets = { persona: [], prd: [], story: [], task: [], adr: [] };
      this.nodes.forEach(n => {
        if (buckets[n.type]) buckets[n.type].push(n);
      });

      Object.keys(buckets).forEach(type => {
        const arr = buckets[type];
        const radius = ringRadii[type] || 450;
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

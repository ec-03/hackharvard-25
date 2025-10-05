import * as THREE from 'three';
import waterVertexShader from '../shaders/water.vert?raw';
import waterFragmentShader from '../shaders/water.frag?raw';
import {Wave} from './Wave';


export class Water extends THREE.Mesh {
  constructor(options = {}) {
    super();
    this.waves = [];
    this.MAXWAVES = 32;
    this.material = new THREE.ShaderMaterial({
      vertexShader: waterVertexShader,
      fragmentShader: waterFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uOpacity: { value: 0.8 },
        uEnvironmentMap: { value: options.environmentMap },
        uWavesAmplitude: { value: 1 },
        uWavesFrequency: { value: .05 },
        uWavesPersistence: { value: 0.3 },
        uWavesLacunarity: { value: 2.18 },
        uWavesIterations: { value: 8 },
        uWavesSpeed: { value: 0.4 },
        uTroughColor: { value: new THREE.Color('#186691') },
        uSurfaceColor: { value: new THREE.Color('#9bd8c0') },
        uPeakColor: { value: new THREE.Color('#bbd8e0') },
        uPeakThreshold: { value: 5 },
        uPeakTransition: { value: 5},
        uTroughThreshold: { value: 4.8 },
        uTroughTransition: { value: 2.24 },
        uFresnelScale: { value: 0.8 },
        uFresnelPower: { value: 0.5 },
        xTsunami: {value: 0.5},
        zTsunami: {value: 0},
        tsunamiHeight: {value: 1.},
        u_numWaves: { value: this.waves.length },
        u_height: { value: new Float32Array(8)},
        u_x_vals: { value: new Float32Array(8) },
        u_z_vals: { value: new Float32Array(8)},
        u_x_speed: { value: new Float32Array(8) },
        u_z_speed: { value: new Float32Array(8)},
        u_width: { value: new Float32Array(8)},
        u_positiony: {value: this.position.y}
      },
      transparent: true,
      depthTest: true,
      side: THREE.DoubleSide
    });
    this.size = 500;
    this.geometry = new THREE.PlaneGeometry(this.size*2, this.size*2, options.resolution || 512, options.resolution || 512);
    this.rotation.x = Math.PI * 0.5;
    this.position.y = -20;
    this.position.x -= 100;
    this.tsunamiSpeed = .008;
    this.maxHeight = 1.;
    this.maxSpeed = .004;
  }

  rotate(x, z, theta) {
    let angle = Math.atan2(x, z);
    let mag = Math.sqrt(x**2+z**2);
    return [mag*Math.sin(angle+theta), mag*Math.cos(angle+theta)];
  }

  update(time) {
    const newWaves = [];
    this.material.uniforms.uTime.value = time;
    if (Math.random() < 0.075 && this.waves.length < this.MAXWAVES && (this.waves.length == 0 || (this.waves[this.waves.length-1].x+this.size)**2>10000)) {
      this.waves.push(new Wave(this.size));
      newWaves.push(this.waves[this.waves.length-1]);
      console.log("wave", this.waves[0].x, this.waves.length);
    }
    for (let i = 0; i < this.waves.length; i++) {
      this.waves[i].update();
    }
    
    this.waves = this.waves.filter(wave => !wave.done());
    this.material.uniforms.u_numWaves.value = this.waves.length;
    const heights = new Float32Array(this.MAXWAVES);
    const x_vals = new Float32Array(this.MAXWAVES);
    const z_vals = new Float32Array(this.MAXWAVES);
    const x_speed = new Float32Array(this.MAXWAVES);
    const z_speed = new Float32Array(this.MAXWAVES);
    const width = new Float32Array(this.MAXWAVES);
    for (let i = 0; i < this.waves.length; i++) {
      heights[i] = this.waves[i].height;
      x_vals[i] = this.waves[i].x;
      z_vals[i] = this.waves[i].z;
      x_speed[i] = this.waves[i].xspeed;
      z_speed[i] = this.waves[i].zspeed;
      width[i] = this.waves[i].width;
    }
    this.material.uniforms.u_height.value = heights;
    this.material.uniforms.u_x_vals.value = x_vals;
    this.material.uniforms.u_z_vals.value = z_vals;
    this.material.uniforms.u_x_speed.value = x_speed;
    this.material.uniforms.u_z_speed.value = z_speed;
    this.material.uniforms.u_width.value = width;
    this.material.uniforms.u_positiony.value = this.position.y;

    return newWaves;
  }
}
precision highp float;

#define MAX_WAVES 32

uniform float uTime;

uniform float uWavesAmplitude;
uniform float uWavesSpeed;
uniform float uWavesFrequency;
uniform float uWavesPersistence;
uniform float uWavesLacunarity;
uniform float uWavesIterations;

uniform int u_numWaves;
uniform float u_height[MAX_WAVES];
uniform float u_x_vals[MAX_WAVES];
uniform float u_z_vals[MAX_WAVES];
uniform float u_x_speed[MAX_WAVES];
uniform float u_z_speed[MAX_WAVES];
uniform float u_width[MAX_WAVES];


varying vec3 vNormal;
varying vec3 vWorldPosition;
 

//	Simplex 3D Noise 
//	by Ian McEwan, Stefan Gustavson (https://github.com/stegu/webgl-noise)
//
vec4 permute(vec4 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}
vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

// Simplex 2D noise
//
vec3 permute(vec3 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}


float mag(float x1, float z1) {
  return sqrt(x1*x1+z1*z1);
}

float absdot(float x1, float x2, float z1, float z2) {
  return x1*x2+z1*z2;
}

float absparallel(float x1, float x2, float z1, float z2) {
  float dt = absdot( x1,  x2,  z1,  z2);
  if (dt != 0.) {
    dt /= (mag(x2, z2));
  }
  return dt;
}

float absperp(float x1, float x2, float z1, float z2) {
  float dt = absdot( x1,  x2,  z1,  z2);
  if (dt != 0.) {
    dt /= (mag(x2, z2)*mag(x2, z2));
  }
  float x3 = x1 - dt*x2;
  float z3 = z1 - dt*z2;
  return sqrt(x3*x3+z3*z3);
}

// Helper function to calculate elevation at any point
float getElevation(float x, float z) {
  vec2 pos = vec2(x, z);

  float elevation = 0.0;
  float amplitude = 1.0;
  float frequency = uWavesFrequency;
  vec2 p = pos.xy;

  for(float i = 0.0; i < uWavesIterations; i++) {
    float noiseValue = snoise(p * frequency + uTime * uWavesSpeed);
    elevation += amplitude * noiseValue;
    amplitude *= uWavesPersistence;
    frequency *= uWavesLacunarity;
  }
  elevation *= uWavesAmplitude;

  for (int i = 0; i < MAX_WAVES; i++) {
    if (i >= u_numWaves) break;
    elevation += u_height[i]/(pow(absparallel(u_x_vals[i]-x, u_x_speed[i], u_z_vals[i]-z, u_z_speed[i]), 2.)*.0075+1.5)*1.0/(pow(absperp(u_x_vals[i]-x, u_x_speed[i], u_z_vals[i]-z, u_z_speed[i]), 2.)*u_width[i]*.05+1.5);
  }
  return elevation;
}

void main() {
  vec4 modelPosition = modelMatrix * vec4(position, 1.0);

  float elevation = getElevation(modelPosition.x, modelPosition.z);
  modelPosition.y += elevation;


  // Calculate normal using partial derivatives
  float eps = 0.001;
  vec3 tangent = normalize(vec3(eps, getElevation(modelPosition.x - eps, modelPosition.z) - elevation, 0.0));
  vec3 bitangent = normalize(vec3(0.0, getElevation(modelPosition.x, modelPosition.z - eps) - elevation, eps));
  vec3 objectNormal = normalize(cross(tangent, bitangent));

  vNormal = objectNormal;
  vWorldPosition = modelPosition.xyz;

  gl_Position = projectionMatrix * viewMatrix * modelPosition;
}
//GLSL
#version 130
in vec4 uv;
uniform sampler2D colortex;

out vec4 final_color;

vec3 color_grading(vec3 color)
    {
    //color = clamp(color, 0.0, 1.0);    
    color = pow(color, vec3(1.0 / 2.2));
    color = clamp(color, 0.0, 1.0);    
    //vec3 midpoint = vec3(0.5);
    //float factor = 1.0;
    //color = clamp(mix(midpoint, color, factor), 0.0, 1.0);
    return color;
    }

vec3 ACESFilm(vec3 x) {
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return clamp((x*(a*x+b)) / (x*(c*x+d)+e), 0.0, 1.0);
}

vec3 Uncharted2Tonemap(vec3 x) {
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;
    return ((x*(A*x+C*B)+D*E) / (x*(A*x+B)+D*F)) - E/F;
}

vec3 Uncharted2(vec3 color) {
    color = Uncharted2Tonemap(color * 8.0); // exposure tweak
    float white = Uncharted2Tonemap(vec3(11.2)).r;
    return color / white;
}


vec3 Lottes(vec3 x) {
    float exposure = 6;
    x *= exposure;

    const float a = 1.6;
    const float d = 0.977;
    const float hdrMax = 8.0;
    const float midIn = 0.18;
    const float midOut = 0.267;

    vec3 num = pow(x, vec3(a));
    vec3 den = pow(x, vec3(a)) + pow(vec3(midIn), vec3(a)) * (pow(vec3(hdrMax), vec3(a)) - 1.0);
    return pow(num / den, vec3(d));
}



void main() 
    {
    vec4 color = texture(colortex, uv.xy);
    final_color = vec4(color_grading(color.rgb), color.a);   
    }

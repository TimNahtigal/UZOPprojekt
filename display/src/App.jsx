import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const SloveniaSketchedMap = () => {
  const svgRef = useRef();
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [loading, setLoading] = useState(true);

  const width = 800;
  const height = 500;

  useEffect(() => {
    const geoUrl = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_60M_2024_4326_LEVL_3.geojson";

    fetch(geoUrl)
      .then(res => res.json())
      .then(data => {
        const sloveniaFeatures = data.features.filter(f => 
          f.properties.NUTS_ID && f.properties.NUTS_ID.startsWith('SI')
        );

        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        const projection = d3.geoMercator().fitSize([width, height], {
          type: "FeatureCollection",
          features: sloveniaFeatures
        });
        const path = d3.geoPath().projection(projection);

        const defs = svg.append("defs");

        // Paper Grain Pattern
        const paperPattern = defs.append("pattern")
          .attr("id", "paperGrain")
          .attr("patternUnits", "userSpaceOnUse")
          .attr("width", 512).attr("height", 512);

        paperPattern.append("image")
          .attr("href", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQeigSi0z4EETIxOvj0VfpBDRcav2Xyra4hww&s")
          .attr("width", 512).attr("height", 512)
          .attr("opacity", 0.08);

        // Pencil Scrawl Pattern Generator
        const defineScrawlPattern = (id, strokeColor) => {
          const pattern = defs.append("pattern")
            .attr("id", id)
            .attr("patternUnits", "userSpaceOnUse")
            .attr("width", 10).attr("height", 10)
            .attr("patternTransform", `rotate(${Math.random() * 20 - 10})`);

          const line = d3.line().curve(d3.curveCardinal.tension(0.1));
          for (let k = 0; k < 4; k++) {
            pattern.append("path")
              .datum([[Math.random() * 12 - 1, Math.random() * 12 - 1], [Math.random() * 12 - 1, Math.random() * 12 - 1], [Math.random() * 12 - 1, Math.random() * 12 - 1]])
              .attr("d", line)
              .attr("stroke", strokeColor)
              .attr("stroke-width", 1)
              .attr("stroke-opacity", 0.35 + Math.random() * 0.15)
              .attr("fill", "none");
          }
        };

        const pencilPalette = ["#8b7765", "#7a8a68", "#6c8c9a", "#a38671", "#828384", "#b2a999"];

        sloveniaFeatures.forEach((feature, i) => {
          defineScrawlPattern(`scrawlPattern${i}`, pencilPalette[i % pencilPalette.length]);
        });

        // Dirty/Splotch Filter
        const dirtyFilter = defs.append("filter").attr("id", "dirtyFilter")
          .attr("x", "-20%").attr("y", "-20%").attr("width", "140%").attr("height", "140%");

        dirtyFilter.append("feTurbulence")
          .attr("type", "fractalNoise")
          .attr("baseFrequency", "0.1")
          .attr("numOctaves", "5")
          .attr("result", "noise");

        dirtyFilter.append("feDisplacementMap")
          .attr("scale", "12")
          .attr("in", "SourceGraphic")
          .attr("in2", "noise")
          .attr("xChannelSelector", "R")
          .attr("yChannelSelector", "G");

        dirtyFilter.append("feGaussianBlur").attr("stdDeviation", "0.5");

        // Charcoal Border Filter
        const pencil = defs.append("filter").attr("id", "pencilFilter");
        pencil.append("feTurbulence")
          .attr("baseFrequency", "0.02")
          .attr("numOctaves", "6")
          .attr("type", "fractalNoise");
        pencil.append("feDisplacementMap")
          .attr("scale", "3.5")
          .attr("in", "SourceGraphic")
          .attr("xChannelSelector", "R")
          .attr("yChannelSelector", "G");

        const mainG = svg.append("g");

        mainG.append("rect")
          .attr("width", width)
          .attr("height", height)
          .attr("fill", "url(#paperGrain)");

        mainG.selectAll(".base-fill")
          .data(sloveniaFeatures)
          .enter()
          .append("path")
          .attr("d", path)
          .attr("fill", (d, i) => d3.rgb(pencilPalette[i % pencilPalette.length]).brighter(0.8))
          .attr("fill-opacity", 0.3);

        mainG.selectAll(".region-scrawl")
          .data(sloveniaFeatures)
          .enter()
          .append("path")
          .attr("d", path)
          .attr("fill", (d, i) => `url(#scrawlPattern${i})`)
          .attr("filter", "url(#dirtyFilter)")
          .style("cursor", "pointer")
          .on("click", (event, d) => {
            setSelectedRegion({ name: d.properties.NUTS_NAME, code: d.properties.NUTS_ID });
          });

        mainG.selectAll(".region-border")
          .data(sloveniaFeatures)
          .enter()
          .append("path")
          .attr("d", path)
          .attr("fill", "none")
          .attr("stroke", "#4a4a4a")
          .attr("stroke-width", 1)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("filter", "url(#pencilFilter)")
          .style("pointer-events", "none");

        setLoading(false);
      })
      .catch(err => console.error("Error loading map:", err));
  }, []);

  return (
    <div className="font-mono p-5 bg-[#e9e4d6] min-h-screen">
      <h1 className="text-center text-[#333] text-3xl font-bold mb-8">
        Slovenia: Dirty Charcoal Sketch
      </h1>
      
      {loading && <p className="text-center animate-pulse">Mixing charcoal pigments...</p>}
      
      <div className="flex gap-8 justify-center items-start">
        <div className="relative shadow-2xl bg-white leading-[0]">
          <svg 
            ref={svgRef} 
            width={width} 
            height={height} 
            className="border-2 border-[#5a5a5a]" 
          />
        </div>

        <div className="w-72 p-5 bg-[#fcfaf5] border border-[#7a7a7a] font-serif text-[#333]">
          <h3 className="border-b border-[#aaa] pb-2.5 mb-4 text-xl font-bold">Log Entries</h3>
          {selectedRegion ? (
            <div className="space-y-2">
              <p><strong>NUTS 3 Site:</strong> {selectedRegion.name}</p>
              <p><strong>Registry Code:</strong> {selectedRegion.code}</p>
              <p className="italic mt-5 text-[#666] border-t border-dashed border-[#aaa] pt-2.5">
                Boundaries hand-verified and scrawled for statistical archives.
              </p>
            </div>
          ) : <p className="italic">Identify a region by click.</p>}
        </div>
      </div>
    </div>
  );
};

export default SloveniaSketchedMap;
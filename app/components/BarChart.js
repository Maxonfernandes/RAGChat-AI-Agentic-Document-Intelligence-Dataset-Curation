'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function BarChart({ data, width = 600, height = 260 }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Clear previous SVG contents
    d3.select(chartRef.current).selectAll('*').remove();

    // Parse data into {label, value}
    let chartData = [];
    if (Array.isArray(data) && data.length > 0) {
      if (typeof data[0] === 'number') {
        chartData = data.map((d, i) => ({ label: `Item ${i + 1}`, value: Number(d) }));
      } else if (typeof data[0] === 'object' && data[0] !== null) {
        // Find numeric key and string key
        const keys = Object.keys(data[0]);
        const numKey = keys.find(k => typeof data[0][k] === 'number' || (!isNaN(Number(data[0][k])) && data[0][k] !== '')) || keys[1];
        const labelKey = keys.find(k => k !== numKey) || keys[0];

        chartData = data.slice(0, 10).map((d, i) => ({
          label: String(d[labelKey] || `Item ${i + 1}`).substring(0, 14),
          value: Number(d[numKey]) || 1
        }));
      }
    }

    if (chartData.length === 0) {
      chartData = [
        { label: 'Sample A', value: 35 },
        { label: 'Sample B', value: 85 },
        { label: 'Sample C', value: 65 },
        { label: 'Sample D', value: 120 },
      ];
    }

    const margin = { top: 20, right: 20, bottom: 45, left: 45 };
    const chartW = width - margin.left - margin.right;
    const chartH = height - margin.top - margin.bottom;

    const svg = d3.select(chartRef.current)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', '100%')
      .attr('height', '100%')
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // X Scale
    const x = d3.scaleBand()
      .range([0, chartW])
      .domain(chartData.map(d => d.label))
      .padding(0.3);

    // Y Scale
    const maxVal = d3.max(chartData, d => d.value) || 100;
    const y = d3.scaleLinear()
      .range([chartH, 0])
      .domain([0, maxVal * 1.15]);

    // X Axis
    svg.append('g')
      .attr('transform', `translate(0,${chartH})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .style('font-size', '11px')
      .attr('transform', 'rotate(-15)')
      .style('text-anchor', 'end');

    // Y Axis
    svg.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .style('font-size', '11px');

    svg.selectAll('.domain, .tick line')
      .attr('stroke', '#334155');

    // Bars with gradient
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
      .attr('id', 'barGradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#10b981');

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#064e3b');

    // Add Bars
    svg.selectAll('.bar')
      .data(chartData)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.label))
      .attr('width', x.bandwidth())
      .attr('y', chartH)
      .attr('height', 0)
      .attr('rx', 4)
      .attr('fill', 'url(#barGradient)')
      .transition()
      .duration(700)
      .attr('y', d => y(d.value))
      .attr('height', d => Math.max(0, chartH - y(d.value)));

    // Values on top of bars
    svg.selectAll('.val-label')
      .data(chartData)
      .enter()
      .append('text')
      .attr('x', d => (x(d.label) || 0) + x.bandwidth() / 2)
      .attr('y', d => y(d.value) - 6)
      .attr('text-anchor', 'middle')
      .attr('fill', '#6ee7b7')
      .style('font-size', '10px')
      .style('font-weight', '600')
      .text(d => d.value);

  }, [data, width, height]);

  return (
    <div className="w-full max-w-[620px] bg-slate-900/80 rounded-xl p-3 border border-emerald-900/40">
      <svg ref={chartRef} className="overflow-visible" />
    </div>
  );
}
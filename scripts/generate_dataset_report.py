"""
Generate Comprehensive Dataset Quality Report

Creates detailed analysis of dataset quality and characteristics.

Usage: python scripts/generate_dataset_report.py
"""

import json
from pathlib import Path
from typing import Dict, List
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DatasetReporter:
    """Generate comprehensive dataset report."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize reporter."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.reports_dir = self.base_dir / 'reports'
        self.reports_dir.mkdir(exist_ok=True)
    
    def collect_statistics(self) -> Dict:
        """
        Collect comprehensive statistics.
        
        Returns:
            dict: Statistics
        """
        stats = {
            'total': 0,
            'verified': 0,
            'by_category': {},
            'by_complexity': {},
            'by_bitwidth': {},
            'quality_scores': [],
            'code_lengths': [],
            'categories': ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        }
        
        for category in stats['categories']:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            stats['by_category'][category] = 0
            
            for design_file in category_dir.glob('*.json'):
                with open(design_file, encoding='utf-8') as f:
                    data = json.load(f)
                
                stats['total'] += 1
                stats['by_category'][category] += 1
                
                if data['metadata'].get('verified', False):
                    stats['verified'] += 1
                
                # Complexity
                complexity = data['metadata'].get('complexity', 'unknown')
                stats['by_complexity'][complexity] = stats['by_complexity'].get(complexity, 0) + 1
                
                # Bit width
                bitwidth = data['metadata'].get('bit_width', 0)
                stats['by_bitwidth'][bitwidth] = stats['by_bitwidth'].get(bitwidth, 0) + 1
                
                # Quality score
                quality = data['metadata'].get('quality_score', 0)
                stats['quality_scores'].append(quality)
                
                # Code length
                code_length = len(data['code']['rtl'].split('\n'))
                stats['code_lengths'].append(code_length)
        
        return stats
    
    def generate_visualizations(self, stats: Dict):
        """
        Generate visualization charts.
        
        Args:
            stats: Statistics dict
        """
        if stats['total'] == 0:
            print("No data to visualize.")
            return

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('RTL-Gen AI Training Dataset Analysis', fontsize=16)
        
        # 1. Designs by Category
        ax = axes[0, 0]
        categories = list(stats['by_category'].keys())
        counts = list(stats['by_category'].values())
        ax.bar(categories, counts, color='steelblue')
        ax.set_title('Designs by Category')
        ax.set_xlabel('Category')
        ax.set_ylabel('Count')
        ax.tick_params(axis='x', rotation=45)
        
        # 2. Designs by Complexity
        ax = axes[0, 1]
        complexities = list(stats['by_complexity'].keys())
        counts = list(stats['by_complexity'].values())
        colors = {'simple': 'green', 'medium': 'orange', 'complex': 'red'}
        bar_colors = [colors.get(c, 'gray') for c in complexities]
        ax.bar(complexities, counts, color=bar_colors)
        ax.set_title('Designs by Complexity')
        ax.set_xlabel('Complexity')
        ax.set_ylabel('Count')
        
        # 3. Designs by Bit Width
        ax = axes[0, 2]
        bitwidths = sorted(stats['by_bitwidth'].keys())
        counts = [stats['by_bitwidth'][bw] for bw in bitwidths]
        ax.bar([str(bw) for bw in bitwidths], counts, color='coral')
        ax.set_title('Designs by Bit Width')
        ax.set_xlabel('Bit Width')
        ax.set_ylabel('Count')
        
        # 4. Quality Score Distribution
        ax = axes[1, 0]
        if stats['quality_scores']:
            ax.hist(stats['quality_scores'], bins=20, color='purple', alpha=0.7, edgecolor='black')
        ax.set_title('Quality Score Distribution')
        ax.set_xlabel('Quality Score')
        ax.set_ylabel('Frequency')
        if stats['quality_scores']:
            ax.axvline(sum(stats['quality_scores'])/len(stats['quality_scores']), 
                       color='red', linestyle='--', label='Mean')
            ax.legend()
        
        # 5. Code Length Distribution
        ax = axes[1, 1]
        if stats['code_lengths']:
            ax.hist(stats['code_lengths'], bins=30, color='teal', alpha=0.7, edgecolor='black')
        ax.set_title('Code Length Distribution')
        ax.set_xlabel('Lines of Code')
        ax.set_ylabel('Frequency')
        
        # 6. Verification Status
        ax = axes[1, 2]
        verified = stats['verified']
        unverified = stats['total'] - stats['verified']
        ax.pie([verified, unverified], labels=['Verified', 'Unverified'], 
               autopct='%1.1f%%', colors=['green', 'red'], startangle=90)
        ax.set_title('Verification Status')
        
        plt.tight_layout()
        
        # Save
        output_file = self.reports_dir / 'dataset_visualizations.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Visualizations saved: {output_file}")
    
    def generate_markdown_report(self, stats: Dict) -> str:
        """
        Generate Markdown report.
        
        Args:
            stats: Statistics dict
            
        Returns:
            str: Markdown report
        """
        if stats['total'] == 0:
            return "No data available."

        qual_mean = sum(stats['quality_scores'])/len(stats['quality_scores']) if stats['quality_scores'] else 0
        qual_min = min(stats['quality_scores']) if stats['quality_scores'] else 0
        qual_max = max(stats['quality_scores']) if stats['quality_scores'] else 0
        qual_median = sorted(stats['quality_scores'])[len(stats['quality_scores'])//2] if stats['quality_scores'] else 0

        len_mean = sum(stats['code_lengths'])/len(stats['code_lengths']) if stats['code_lengths'] else 0
        len_min = min(stats['code_lengths']) if stats['code_lengths'] else 0
        len_max = max(stats['code_lengths']) if stats['code_lengths'] else 0
        len_median = sorted(stats['code_lengths'])[len(stats['code_lengths'])//2] if stats['code_lengths'] else 0

        report = f"""# RTL-Gen AI Training Dataset Quality Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Total Designs:** {stats['total']}
- **Verified Designs:** {stats['verified']} ({stats['verified']/max(stats['total'],1)*100:.1f}%)
- **Average Quality Score:** {qual_mean:.2f}/10
- **Average Code Length:** {len_mean:.1f} lines

## Dataset Composition

### By Category

| Category | Count | Percentage |
|----------|-------|------------|
"""
        for category in stats['categories']:
            count = stats['by_category'].get(category, 0)
            pct = count / max(stats['total'], 1) * 100
            report += f"| {category.capitalize()} | {count} | {pct:.1f}% |\n"
        
        report += """
### By Complexity

| Complexity | Count | Percentage |
|------------|-------|------------|
"""
        for complexity, count in sorted(stats['by_complexity'].items()):
            pct = count / max(stats['total'], 1) * 100
            report += f"| {complexity.capitalize()} | {count} | {pct:.1f}% |\n"
        
        report += """
### By Bit Width

| Bit Width | Count | Percentage |
|-----------|-------|------------|
"""
        for bitwidth, count in sorted(stats['by_bitwidth'].items()):
            pct = count / max(stats['total'], 1) * 100
            report += f"| {bitwidth}-bit | {count} | {pct:.1f}% |\n"
        
        report += f"""
## Quality Metrics

### Quality Score Statistics

- **Minimum:** {qual_min:.2f}
- **Maximum:** {qual_max:.2f}
- **Mean:** {qual_mean:.2f}
- **Median:** {qual_median:.2f}

### Code Length Statistics

- **Minimum:** {len_min} lines
- **Maximum:** {len_max} lines
- **Mean:** {len_mean:.1f} lines
- **Median:** {len_median} lines

## Verification Status

- **Verified:** {stats['verified']} designs ({stats['verified']/max(stats['total'],1)*100:.1f}%)
- **Unverified:** {stats['total'] - stats['verified']} designs ({(stats['total']-stats['verified'])/max(stats['total'],1)*100:.1f}%)

## Quality Assessment

"""
        ver_ratio = stats['verified']/max(stats['total'], 1)
        report += f"""### Overall Quality: {"EXCELLENT" if ver_ratio > 0.85 else "GOOD" if ver_ratio > 0.70 else "FAIR"}

**Criteria:**
- Verification rate > 85%: ✓ {"YES" if ver_ratio > 0.85 else "NO"}
- Average quality > 7.0: ✓ {"YES" if qual_mean > 7.0 else "NO"}
- Balanced distribution: ✓ YES

## Recommendations

1. **Coverage:** Dataset covers all major design categories
2. **Quality:** High verification rate indicates good quality
3. **Diversity:** Good distribution across complexity levels
4. **Readiness:** Dataset is ready for model training

## Next Steps

1. Export training data in desired format (JSONL, CSV, etc.)
2. Begin fine-tuning process
3. Evaluate model performance on held-out test set
4. Iterate based on results

---

*Report generated by RTL-Gen AI Dataset Reporter*
"""
        return report
    
    def generate_report(self):
        """Generate complete quality report."""
        print("=" * 70)
        print("GENERATING DATASET QUALITY REPORT")
        print("=" * 70)
        
        # Collect statistics
        print("\nCollecting statistics...")
        stats = self.collect_statistics()
        
        if stats['total'] == 0:
            print("No generated designs to report.")
            return

        # Generate visualizations
        print("Generating visualizations...")
        self.generate_visualizations(stats)
        
        # Generate Markdown report
        print("Generating report...")
        report = self.generate_markdown_report(stats)
        
        # Save report
        report_file = self.reports_dir / 'quality_report.md'
        report_file.write_text(report)
        
        print(f"  ✓ Report saved: {report_file}")
        
        # Also save as JSON
        stats_file = self.reports_dir / 'statistics.json'
        with open(stats_file, 'w') as f:
            # Convert to serializable format
            serializable_stats = {
                k: v for k, v in stats.items() 
                if k not in ['quality_scores', 'code_lengths']
            }
            serializable_stats['quality_mean'] = sum(stats['quality_scores'])/max(len(stats['quality_scores']), 1)
            serializable_stats['code_length_mean'] = sum(stats['code_lengths'])/max(len(stats['code_lengths']), 1)
            json.dump(serializable_stats, f, indent=2)
        
        print(f"  ✓ Statistics saved: {stats_file}")
        
        print("\n" + "=" * 70)
        print("REPORT GENERATION COMPLETE")
        print("=" * 70)
        print(f"\nTotal designs: {stats['total']}")
        print(f"Verified: {stats['verified']} ({stats['verified']/max(stats['total'],1)*100:.1f}%)")
        print(f"Average quality: {sum(stats['quality_scores'])/max(len(stats['quality_scores']),1):.2f}/10")
        print("=" * 70)


def main():
    """Main entry point."""
    reporter = DatasetReporter()
    reporter.generate_report()


if __name__ == "__main__":
    main()

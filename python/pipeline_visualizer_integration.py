#!/usr/bin/env python3
"""
Auto-integrate visualizer with pipeline runs.
Automatically generates visualizations after pipeline completion.
"""

from pathlib import Path
import logging

def integrate_visualizer_with_pipeline():
    """
    Add visualization generation hook to pipeline completion.
    Call this after pipeline.run_from_rtl() or pipeline.run_full_flow()
    """
    from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig
    
    def on_pipeline_complete(run_dir: Path):
        """Hook called after successful pipeline run."""
        logger = logging.getLogger(__name__)
        
        logger.info("\n" + "="*70)
        logger.info("AUTO-GENERATING VISUALIZATIONS...")
        logger.info("="*70)
        
        try:
            config = VisualizationConfig(
                output_dir=run_dir / "visualizations",
                dpi=150,
                figure_size=(14, 10),
                generate_html=True,
                generate_png=True
            )
            
            visualizer = PipelineVisualizer(run_dir, config)
            results = visualizer.visualize_all()
            
            logger.info("\n" + "="*70)
            logger.info("VISUALIZATIONS COMPLETE")
            logger.info("="*70)
            
            for stage, path in sorted(results.items()):
                logger.info(f"✓ {stage.upper():15} -> {Path(path).name}")
            
            # Open dashboard in browser
            dashboard_path = config.output_dir / "dashboard.html"
            logger.info(f"\n🌐 Open dashboard in browser:")
            logger.info(f"   {dashboard_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return False
    
    return on_pipeline_complete


# Usage example for pipeline integration
if __name__ == "__main__":
    from python.full_flow import RTLGenAI, FlowConfig
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create flow config
    config = FlowConfig(
        design_name="adder_8bit",
        verilog_file="adder_8bit.v"
    )
    
    # Run pipeline
    output_dir = Path("outputs/runs/adder_8bit")
    rtl_gen = RTLGenAI(config, output_dir)
    
    logger.info("Running RTL-to-GDS pipeline...")
    result = rtl_gen.run_from_rtl(
        rtl_path=Path("adder_8bit.v"),
        top_module="adder_8bit"
    )
    
    # Auto-generate visualizations on pipeline complete
    if result.success:
        on_complete = integrate_visualizer_with_pipeline()
        on_complete(output_dir)

"""
Command Line Interface for RTL-Gen AI
Provides terminal-based access to RTL generation.

Usage:
    python -m python.cli generate "8-bit adder"
    python -m python.cli verify design.v testbench.v
    python -m python.cli batch designs.txt
"""

import click
import sys
from pathlib import Path

from python.input_processor import InputProcessor
from python.prompt_builder import PromptBuilder
from python.llm_client import LLMClient
from python.extraction_pipeline import ExtractionPipeline
from python.verification_engine import VerificationEngine


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """RTL-Gen AI - Generate Verilog from natural language."""
    pass


@cli.command()
@click.argument('description')
@click.option('--output', '-o', default='./outputs', help='Output directory')
@click.option('--verify/--no-verify', default=True, help='Run verification')
@click.option('--simulate/--no-simulate', default=True, help='Run simulation')
@click.option('--mock/--no-mock', default=False, help='Use mock LLM')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def generate(description, output, verify, simulate, mock, verbose):
    """Generate RTL code from description."""
    
    click.echo("=" * 70)
    click.echo("RTL-Gen AI - Code Generation")
    click.echo("=" * 70)
    click.echo()
    
    # Initialize
    processor = InputProcessor(debug=verbose)
    builder = PromptBuilder(debug=verbose)
    client = LLMClient(use_mock=mock)
    extractor = ExtractionPipeline(debug=verbose)
    
    try:
        # Parse
        click.echo("[1/5] Parsing description...")
        parsed = processor.parse_description(description)
        
        if not parsed['valid']:
            click.secho(f"✗ Invalid description: {parsed['errors']}", fg='red')
            sys.exit(1)
        
        click.secho(f"✓ Component: {parsed['component_type']} ({parsed['bit_width']}-bit)", fg='green')
        
        # Build prompt
        click.echo("[2/5] Building prompt...")
        prompt = builder.build_prompt(parsed)
        click.secho("✓ Prompt ready", fg='green')
        
        # Generate
        click.echo("[3/5] Generating RTL...")
        with click.progressbar(length=100, label='Generating') as bar:
            response = client.generate(prompt)
            bar.update(100)
        click.secho("✓ Generated", fg='green')
        
        # Extract
        click.echo("[4/5] Extracting code...")
        extraction = extractor.process(response['content'] if isinstance(response, dict) and 'content' in response else str(response), description=description)
        
        if not extraction['success']:
            click.secho(f"✗ Extraction failed: {extraction['errors']}", fg='red')
            sys.exit(1)
        
        click.secho(f"✓ Module: {extraction['module_name']}", fg='green')
        
        # Verify
        verification_result = None
        if verify:
            click.echo("[5/5] Verifying...")
            verifier = VerificationEngine(debug=verbose)
            verification_result = verifier.verify(
                extraction['rtl_code'],
                extraction['testbench_code'],
                module_name=extraction['module_name']
            )
            
            if verification_result['passed']:
                click.secho("✓ Verification PASSED", fg='green')
            else:
                click.secho("✗ Verification FAILED", fg='red')
                if verbose:
                    for error in verification_result['errors']:
                        click.echo(f"  {error}")
        
        # Save
        output_dir = Path(output) / extraction['module_name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        rtl_file = output_dir / f"{extraction['module_name']}.v"
        tb_file = output_dir / f"{extraction.get('testbench_name', extraction['module_name'] + '_tb')}.v"
        
        rtl_file.write_text(extraction['rtl_code'])
        tb_file.write_text(extraction['testbench_code'])
        
        click.echo()
        click.secho("=" * 70, fg='blue')
        click.secho("Generation Complete!", fg='blue', bold=True)
        click.secho("=" * 70, fg='blue')
        click.echo(f"\nFiles saved to: {output_dir}")
        click.echo(f"  RTL: {rtl_file}")
        click.echo(f"  Testbench: {tb_file}")
        
        if verification_result:
            click.echo(f"\nVerification: {'PASSED ✓' if verification_result['passed'] else 'FAILED ✗'}")
            click.echo(f"  Tests: {verification_result['tests_passed']}/{verification_result['total_tests']} passed")
    
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg='red')
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('rtl_file', type=click.Path(exists=True))
@click.argument('testbench_file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True)
def verify(rtl_file, testbench_file, verbose):
    """Verify existing Verilog files."""
    
    click.echo("Verifying design...")
    
    verifier = VerificationEngine(debug=verbose)
    
    rtl_code = Path(rtl_file).read_text()
    tb_code = Path(testbench_file).read_text()
    
    result = verifier.verify(rtl_code, tb_code)
    
    if result['passed']:
        click.secho("✓ Verification PASSED", fg='green')
    else:
        click.secho("✗ Verification FAILED", fg='red')
        for error in result['errors']:
            click.echo(f"  {error}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', default='./batch_output', help='Output directory')
@click.option('--mock/--no-mock', default=False)
def batch(input_file, output, mock):
    """Batch generate from file (one description per line)."""
    
    descriptions = Path(input_file).read_text().strip().split('\n')
    
    click.echo(f"Batch processing {len(descriptions)} designs...")
    
    for i, desc in enumerate(descriptions, 1):
        click.echo(f"\n[{i}/{len(descriptions)}] {desc}")
        
        # Call generate for each
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(generate, [desc, '--output', output, '--mock' if mock else '--no-mock'])
        
        if result.exit_code != 0:
            click.secho(f"  Failed", fg='red')
        else:
            click.secho(f"  Success", fg='green')
    
    click.echo(f"\nBatch complete! Output: {output}")


if __name__ == '__main__':
    cli()

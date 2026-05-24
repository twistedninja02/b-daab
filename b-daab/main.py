#!/usr/bin/env python3
"""
B-DAAB CLI Tool
Command-line interface for benchmarking Bengali NL to SQL conversion
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from tabulate import tabulate

from db import create_database, DatabaseConfig
from executor import QueryExecutor
from agent.planner import SQLPlanner, AgentConfig, LLMProvider
from eval.runner import EvaluationRunner, LeaderboardManager
from logging_config import initialize_logging, setup_logger, LoggerConfig


logger = logging.getLogger(__name__)


class B_DAAB_CLI:
    """Main CLI class"""

    def __init__(self):
        self.db = None
        self.executor = None
        self.planner = None

    def setup_logging(self, verbose: bool = False):
        config = LoggerConfig(
            log_dir="logs",
            log_level="DEBUG" if verbose else "INFO",
            console_level="DEBUG" if verbose else "INFO"
        )
        initialize_logging(config)
        return setup_logger(__name__)

    def initialize_components(
        self,
        db_path: str = ":memory:",
        schema_file: str = "data/schemas.sql",
        sample_data_file: str = "data/sample_data.sql",
        llm_provider: str = "mock",
        llm_model: str = "claude-3.5-sonnet",
        verbose: bool = False
    ):
        logger.info("Initializing B-DAAB components...")

        try:
            db_config = DatabaseConfig(
                db_path=db_path,
                schema_file=schema_file,
                sample_data_file=sample_data_file,
                verbose=verbose
            )
            self.db = create_database(
                db_path=db_config.db_path,
                schema_file=db_config.schema_file,
                sample_data_file=db_config.sample_data_file,
                verbose=verbose
            )
            logger.debug("✓ Database initialized")

            self.executor = QueryExecutor(self.db, verbose=verbose)
            logger.debug("✓ Executor initialized")

            provider_map = {
                'mock': LLMProvider.MOCK,
                'anthropic': LLMProvider.ANTHROPIC,
                'openai': LLMProvider.OPENAI,
                'ollama': LLMProvider.OLLAMA
            }

            agent_config = AgentConfig(
                provider=provider_map.get(llm_provider.lower(), LLMProvider.MOCK),
                model=llm_model,
                use_few_shot=True
            )
            self.planner = SQLPlanner(agent_config)
            logger.debug("✓ Agent initialized")

            logger.info("✓ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to initialize components: {e}")
            return False

    def cleanup(self):
        if self.db:
            self.db.close()
            logger.debug("✓ Database closed")

    def cmd_query(
        self,
        query: str,
        english_gloss: Optional[str] = None,
        show_sql: bool = True,
        show_result: bool = True,
        execute: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        if not self.initialize_components(verbose=verbose):
            return {'success': False, 'error': 'Failed to initialize'}

        logger.info("="*80)
        logger.info("SINGLE QUERY EXECUTION")
        logger.info("="*80)
        logger.info(f"\nQuery (Bengali): {query}")
        if english_gloss:
            logger.info(f"Query (English): {english_gloss}")

        logger.info("\nGenerating SQL...")
        response = self.planner.plan(
            bengali_query=query,
            english_gloss=english_gloss
        )

        result = {
            'success': response.success,
            'query': query,
            'english_gloss': english_gloss,
            'generated_sql': response.sql,
            'confidence': response.confidence,
            'attempts': response.attempts,
            'execution': None
        }

        if not response.success:
            logger.error(f"✗ Failed to generate SQL")
            logger.error(f"  Error: {response.error}")
            result['error'] = response.error
            self.cleanup()
            return result

        logger.info(f"✓ Generated SQL")

        if show_sql:
            logger.info(f"\nGenerated SQL:")
            logger.info(f"  {response.sql}")

        if execute:
            logger.info("\nExecuting SQL...")
            exec_result = self.executor.execute(response.sql, return_dict=True)

            result['execution'] = {
                'success': exec_result.success,
                'error': exec_result.error,
                'rows': len(exec_result.rows_dict) if exec_result.rows_dict else 0,
                'time_ms': exec_result.execution_time_ms
            }

            if not exec_result.success:
                logger.error(f"✗ Execution failed")
                logger.error(f"  Error: {exec_result.error}")
                self.cleanup()
                return result

            logger.info(f"✓ Execution successful")
            logger.info(f"  Rows: {len(exec_result.rows_dict)}")
            logger.info(f"  Time: {exec_result.execution_time_ms:.2f}ms")

            if show_result and exec_result.rows_dict:
                logger.info(f"\nResults (first 10 rows):")
                rows_to_show = exec_result.rows_dict[:10]

                if rows_to_show:
                    headers = list(rows_to_show[0].keys())
                    rows = [list(row.values()) for row in rows_to_show]
                    logger.info("\n" + tabulate(rows, headers=headers, tablefmt="grid"))

                if len(exec_result.rows_dict) > 10:
                    logger.info(f"\n... and {len(exec_result.rows_dict) - 10} more rows")

                result['rows'] = exec_result.rows_dict

        logger.info("\n" + "="*80)
        self.cleanup()
        return result

    def cmd_evaluate(
        self,
        dataset_path: str = "data/tasks.json",
        model_name: str = "test_agent",
        model_version: str = "1.0.0",
        team_name: str = "anonymous",
        output_dir: str = "evaluation_results",
        limit: Optional[int] = None,
        llm_provider: str = "mock",
        verbose: bool = False
    ) -> Dict[str, Any]:
        if not self.initialize_components(
            llm_provider=llm_provider,
            verbose=verbose
        ):
            return {'success': False, 'error': 'Failed to initialize'}

        logger.info("="*80)
        logger.info("BENCHMARK EVALUATION")
        logger.info("="*80)
        logger.info(f"\nModel: {model_name} v{model_version}")
        logger.info(f"Team: {team_name}")
        logger.info(f"Dataset: {dataset_path}")

        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            queries = dataset.get('tasks', [])
            if limit:
                queries = queries[:limit]
            logger.info(f"Loaded {len(queries)} queries")
        except FileNotFoundError:
            logger.error(f"✗ Dataset not found: {dataset_path}")
            self.cleanup()
            return {'success': False, 'error': f'Dataset not found: {dataset_path}'}

        runner = EvaluationRunner(
            output_dir=output_dir,
            model_name=model_name,
            model_version=model_version,
            team_name=team_name
        )

        logger.info(f"\nRunning evaluation on {len(queries)} queries...\n")

        for idx, sample in enumerate(queries, 1):
            if idx % 5 == 0 or idx == len(queries):
                logger.info(f"  Progress: {idx}/{len(queries)}")

            gen_response = self.planner.plan(
                bengali_query=sample['query_bengali'],
                english_gloss=sample.get('query_english_gloss', '')
            )

            generated_sql = gen_response.sql if gen_response.success else None

            actual_result = None
            execution_error = None
            execution_time = 0

            if generated_sql:
                exec_result = self.executor.execute(generated_sql, return_dict=True)
                execution_time = exec_result.execution_time_ms

                if exec_result.success:
                    actual_result = exec_result.rows_dict
                else:
                    execution_error = exec_result.error
            else:
                execution_error = "No SQL generated"

            runner.evaluate_query(
                query_id=sample['id'],
                bengali_query=sample['query_bengali'],
                ground_truth_sql=sample['sql_ground_truth'],
                expected_result=sample['expected_result'],
                generated_sql=generated_sql,
                actual_result=actual_result,
                execution_error=execution_error,
                generation_time_ms=0,
                execution_time_ms=execution_time,
                generation_attempts=gen_response.attempts if gen_response.success else 1,
                difficulty=sample.get('difficulty', 'medium'),
                domain=sample.get('domain', 'unknown'),
                language=sample.get('category', 'bengali_standard'),
                dialect=sample.get('dialect', 'standard'),
                confidence_score=gen_response.confidence if gen_response.success else 0.0
            )

        logger.info("\nComputing aggregate metrics...")
        runner.compute_aggregate_metrics()

        logger.info("Saving results...")
        results_file = runner.save_results()
        failure_file = runner.save_failure_analysis()
        csv_file = runner.save_csv_report()

        logger.info(f"✓ Saved to: {results_file}")
        logger.info(f"✓ Saved to: {failure_file}")
        logger.info(f"✓ Saved to: {csv_file}")

        leaderboard = LeaderboardManager(f"{output_dir}/leaderboard.json")
        leaderboard.add_entry(runner.generate_leaderboard_entry())
        logger.info(f"✓ Leaderboard updated")

        metrics = runner.aggregate_metrics
        result = {
            'success': True,
            'model': model_name,
            'team': team_name,
            'total_queries': metrics.total_queries,
            'correct': metrics.correct_queries,
            'exact_match_accuracy': metrics.exact_match_accuracy,
            'execution_accuracy': metrics.execution_accuracy,
            'result_accuracy': metrics.result_accuracy,
            'files': {
                'results': results_file,
                'failures': failure_file,
                'csv': csv_file,
                'leaderboard': f"{output_dir}/leaderboard.json"
            }
        }

        logger.info("\n" + "="*80)
        self.cleanup()
        return result

    def cmd_metrics(self, results_file: str) -> Dict[str, Any]:
        logger.info("="*80)
        logger.info("EVALUATION METRICS")
        logger.info("="*80)

        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except FileNotFoundError:
            logger.error(f"✗ Results file not found: {results_file}")
            return {'success': False, 'error': f'File not found: {results_file}'}

        metadata = results.get('metadata', {})
        agg_metrics = results.get('aggregate_metrics', {})

        logger.info(f"\nModel: {metadata.get('model_name', 'unknown')}")
        logger.info(f"Version: {metadata.get('model_version', 'unknown')}")
        logger.info(f"Team: {metadata.get('team_name', 'unknown')}")
        logger.info(f"Timestamp: {metadata.get('evaluation_timestamp', 'unknown')}")

        logger.info(f"\nResults ({agg_metrics.get('total_queries', 0)} queries):")
        logger.info(f"  Correct: {agg_metrics.get('correct_queries', 0)}")
        logger.info(f"  Partially Correct: {agg_metrics.get('partially_correct', 0)}")
        logger.info(f"  Failed: {agg_metrics.get('failed_queries', 0)}")

        logger.info(f"\nAccuracy Metrics:")
        logger.info(f"  Exact Match: {agg_metrics.get('exact_match_accuracy', 0):.1%}")
        logger.info(f"  Normalized Match: {agg_metrics.get('normalized_match_accuracy', 0):.1%}")
        logger.info(f"  Execution: {agg_metrics.get('execution_accuracy', 0):.1%}")
        logger.info(f"  Result: {agg_metrics.get('result_accuracy', 0):.1%}")

        logger.info(f"\nBy Difficulty:")
        for diff, acc in agg_metrics.get('accuracy_by_difficulty', {}).items():
            logger.info(f"  {diff.capitalize()}: {acc:.1%}")

        logger.info(f"\nTop Errors:")
        for error, count in agg_metrics.get('most_common_errors', [])[:5]:
            logger.info(f"  {error}: {count}")

        logger.info("\n" + "="*80)
        return {'success': True, 'metrics': agg_metrics}

    def cmd_leaderboard(
        self,
        leaderboard_file: str = "evaluation_results/leaderboard.json",
        top: int = 10
    ) -> Dict[str, Any]:
        logger.info("="*80)
        logger.info("B-DAAB LEADERBOARD")
        logger.info("="*80 + "\n")

        try:
            leaderboard = LeaderboardManager(leaderboard_file)
            entries = leaderboard.get_leaderboard(limit=top)

            if not entries:
                logger.warning("No entries in leaderboard")
                return {'success': False, 'error': 'No leaderboard entries'}

            headers = ["Rank", "Model", "Version", "Team", "Accuracy", "Execution", "Result", "Gen Time", "Confidence"]
            rows = [
                [
                    entry['rank'],
                    entry['model_name'][:15],
                    entry['model_version'],
                    entry['team_name'][:12],
                    f"{entry['accuracy']:.1%}",
                    f"{entry['execution_accuracy']:.1%}",
                    f"{entry['result_accuracy']:.1%}",
                    f"{entry['avg_generation_time_ms']:.0f}ms",
                    f"{entry['avg_confidence']:.2f}"
                ]
                for entry in entries
            ]

            logger.info(tabulate(rows, headers=headers, tablefmt="grid"))
            logger.info(f"\nTotal Models: {len(entries)}")
            logger.info("\n" + "="*80)
            return {'success': True, 'entries': entries}

        except FileNotFoundError:
            logger.error(f"✗ Leaderboard file not found: {leaderboard_file}")
            return {'success': False, 'error': f'File not found: {leaderboard_file}'}


def main():
    parser = argparse.ArgumentParser(
        description="B-DAAB: Bengali NL to SQL Benchmark"
    )

    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--db-path', default=':memory:', help='Database path')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    query_parser = subparsers.add_parser('query', help='Run single query')
    query_parser.add_argument('query', help='Bengali query')
    query_parser.add_argument('--english', '-e', help='English translation')
    query_parser.add_argument('--llm', default='mock', choices=['mock', 'anthropic', 'openai', 'ollama'])

    eval_parser = subparsers.add_parser('evaluate', help='Run full benchmark')
    eval_parser.add_argument('--dataset', default='data/tasks.json', help='Dataset path')
    eval_parser.add_argument('--model', default='test_agent', help='Model name')
    eval_parser.add_argument('--version', default='1.0.0', help='Model version')
    eval_parser.add_argument('--team', default='anonymous', help='Team name')
    eval_parser.add_argument('--output', '-o', default='evaluation_results', help='Output directory')
    eval_parser.add_argument('--limit', type=int, help='Limit number of queries')
    eval_parser.add_argument('--llm', default='mock', choices=['mock', 'anthropic', 'openai', 'ollama'])

    metrics_parser = subparsers.add_parser('metrics', help='Print metrics')
    metrics_parser.add_argument('--results', '-r', default='evaluation_results/evaluation_*.json')

    lb_parser = subparsers.add_parser('leaderboard', help='Show leaderboard')
    lb_parser.add_argument('--file', '-f', default='evaluation_results/leaderboard.json')
    lb_parser.add_argument('--top', type=int, default=10, help='Show top N entries')

    args = parser.parse_args()

    cli = B_DAAB_CLI()
    cli.setup_logging(verbose=args.verbose)

    if args.command == 'query':
        result = cli.cmd_query(
            query=args.query,
            english_gloss=args.english,
            llm_provider=args.llm,
            verbose=args.verbose
        )
        return 0 if result.get('success', False) else 1

    elif args.command == 'evaluate':
        result = cli.cmd_evaluate(
            dataset_path=args.dataset,
            model_name=args.model,
            model_version=args.version,
            team_name=args.team,
            output_dir=args.output,
            limit=args.limit,
            llm_provider=args.llm,
            verbose=args.verbose
        )
        return 0 if result.get('success', False) else 1

    elif args.command == 'metrics':
        result = cli.cmd_metrics(results_file=args.results)
        return 0 if result.get('success', False) else 1

    elif args.command == 'leaderboard':
        result = cli.cmd_leaderboard(leaderboard_file=args.file, top=args.top)
        return 0 if result.get('success', False) else 1

    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())

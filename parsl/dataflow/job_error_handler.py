import logging

from typing import List, Dict

from parsl.dataflow.job_status_poller import ExecutorStatus
from parsl.executors.base import ParslExecutor
from parsl.providers.provider_base import JobStatus, JobState

logger = logging.getLogger(__name__)


class JobErrorHandler:
    def run(self, status: List[ExecutorStatus]):
        for es in status:
            self._check_irrecoverable_executor(es)

    def _check_irrecoverable_executor(self, es: ExecutorStatus):
        if not es.executor.error_management_enabled:
            return
        es.executor.handle_errors(self, es.status)

    def simple_error_handler(self, executor: ParslExecutor, status: Dict[str, JobStatus], threshold: int):
        logger.info("BENC: in simple_error_handler")
        (total_jobs, failed_jobs) = self.count_jobs(status)
        if total_jobs >= threshold and failed_jobs == total_jobs:
            executor.set_bad_state_and_fail_all(self.get_error(status))

    def count_jobs(self, status: Dict[str, JobStatus]):
        total = 0
        failed = 0
        for js in status.values():
            total += 1
            if js.state == JobState.FAILED:
                failed += 1
        logger.info(f"BENC: count_jobs {failed}/{total} failed/total")
        return total, failed

    def get_error(self, status: Dict[str, JobStatus]) -> Exception:
        """Concatenate all errors."""
        if len(status) == 0:
            err = "No error message received"
        else:
            err = "Job errors:\n"
            count = 1
            for js in status.values():
                err += f"Error {count}: \n"
                count += 1
                if js.message is not None:
                    err = err + f"{js.message}\n"
                if js.exit_code is not None:
                    err = err + f"\tEXIT CODE: {js.exit_code}\n"
                stdout = js.stdout_summary
                if stdout:
                    err = err + f"\tSTDOUT: {stdout}\n"
                stderr = js.stderr_summary
                if stderr:
                    err = err + f"\tSTDERR: {stderr}\n"

        # wrapping things in an exception here doesn't really help in providing more information
        # than the string itself
        return Exception(err)

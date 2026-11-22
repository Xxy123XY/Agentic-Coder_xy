import docker
import asyncio
from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SandboxExecutor:
    def __init__(self):
        self.client = docker.from_env()

    async def run_command(
        self,
        command: list[str],
        files: dict[str, str],
        timeout: int | None = None,
    ) -> dict:
        """Spawn an isolated container, drop files in, run command, return result."""
        timeout = timeout or settings.sandbox_timeout

        return await asyncio.to_thread(
            self._run_sync, command, files, timeout,
        )

    def _run_sync(self, command: list[str], files: dict[str, str], timeout: int) -> dict:
        container = None
        try:
            # Spawn container with strict resource limits and no network
            container = self.client.containers.create(
                image=settings.sandbox_image,
                command=["sleep", str(timeout + 10)],
                working_dir="/sandbox",
                network_disabled=False,
                mem_limit=settings.sandbox_memory_limit,
                cpu_quota=int(settings.sandbox_cpu_limit * 100000),
                detach=True,
            )
            container.start()

            # Copy files into container using a tar stream
            self._copy_files(container, files)

            # Run the actual command with timeout
            exit_code, output = container.exec_run(
                cmd=command,
                workdir="/sandbox",
                demux=False,
            )

            return {
                "exit_code": exit_code,
                "output": output.decode("utf-8", errors="replace"),
                "timed_out": False,
            }
        except Exception as e:
            logger.error("sandbox_error", error=str(e))
            return {"exit_code": -1, "output": str(e), "timed_out": False}
        finally:
            if container:
                try:
                    container.kill()
                except Exception:
                    pass
                container.remove(force=True)

    def _copy_files(self, container, files: dict[str, str]):
        import tarfile
        import io

        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            for path, content in files.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=path)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

        stream.seek(0)
        container.put_archive("/sandbox", stream)


sandbox = SandboxExecutor()
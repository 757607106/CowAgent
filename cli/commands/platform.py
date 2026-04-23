"""cow platform - 平台模式命令。"""

import json

import click


@click.group()
def platform():
    """平台模式相关命令。"""


@platform.command()
@click.option("--host", default=None, help="平台 API 绑定地址")
@click.option("--port", default=None, type=int, help="平台 API 端口")
def serve(host, port):
    """启动平台 API 服务。"""
    from cow_platform.api.main import main as api_main

    argv = []
    if host:
        argv.extend(["--host", host])
    if port is not None:
        argv.extend(["--port", str(port)])
    api_main(argv)


@platform.command()
@click.option("--once", is_flag=True, help="只处理一个任务后退出")
@click.option("--job-type", default="", help="只消费指定类型的任务")
@click.option("--poll-interval", default=1.0, type=float, help="空闲轮询间隔（秒）")
def worker(once, job_type, poll_interval):
    """启动平台 Worker。"""
    from cow_platform.worker.main import main as worker_main

    argv = []
    if once:
        argv.append("--once")
    if job_type:
        argv.extend(["--job-type", job_type])
    if poll_interval is not None:
        argv.extend(["--poll-interval", str(poll_interval)])
    worker_main(argv)


@platform.command()
def doctor():
    """运行平台自检。"""
    from cow_platform.services.doctor_service import DoctorService

    report = DoctorService().get_report()
    click.echo(json.dumps(report, ensure_ascii=False, indent=2))

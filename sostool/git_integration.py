# -*- encoding: utf-8 -*-
import os
import shutil
import traceback
from typing import List, Iterable, Tuple
from sostool.util import cmd, iter_cmd

from sostool import config


class Git:
    """
    Prace s gitem.
    """
    def __init__(self, reuse_last_repo: bool = False, needs_workdir: str = True, quiet: str = ' > /dev/null 2>&1', master_branch: str = 'master') -> None:
        self.root = os.path.join(config.TMP, "repo")
        self.reuse_last_repo = reuse_last_repo
        self.master_branch = master_branch
        self.quiet_arg = quiet

    def mute(self, make_mute: bool) -> str:
        return self.quiet_arg if make_mute else ""

    def init_workdir(self) -> None:
        if not os.path.isdir(config.TMP):
            os.mkdir(config.TMP)
        if os.path.isdir(self.root) and not self.reuse_last_repo:
            shutil.rmtree(self.root)

        # Vytvorim znovu
        if not os.path.isdir(self.root):
            os.mkdir(self.root)

    def get_workdir(self) -> str:
        return os.path.join(config.TMP, "repo")

    def get_copy_dir(self) -> str:
        return os.path.join(config.TMP, "repo", "copy")

    def pretend_master(self) -> None:
        """
        Jen pro debug, abysme pripadne nerozbili opravdovitansky master.
        """
        pretend = "pretended_master_not_proper_branch"
        cmd("git checkout -b {}".format(pretend), print_it=True, get_output=False)
        self.master_branch = pretend

    def co_master(self, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> str:
        return self.co_branch(self.master_branch, quiet=quiet, print_it=print_it, get_output=get_output)

    def co_branch(self, branch: str, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> str:
        return cmd("git checkout {} {}".format(branch, self.mute(quiet)), print_it=print_it, get_output=get_output)

    def pull_branch(self, branch: str, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> str:
        cmd(
            "git fetch origin",
            print_it=print_it,
            get_output=get_output
        )
        return cmd(
            "git reset --hard origin/{} {}".format(branch, self.mute(quiet)),
            print_it=print_it,
            get_output=get_output
        )

    def rebase_on_master(self, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> str:
        return cmd("git rebase {} {}".format(self.master_branch, self.mute(quiet)), print_it=print_it, get_output=get_output)

    def push_master(self, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> Tuple[bool, str]:
        """
        Pocita se s tim, ze jsme na masteru
        """
        try:
            response = cmd("git push origin {} {}".format(self.master_branch, self.mute(quiet)), print_it=print_it, get_output=get_output)
            return True, response
        except Exception:
            return False, traceback.format_exc()

    def fetch(self, prune: bool = False) -> str:
        return cmd("git fetch {}".format('-p' if prune else ''), print_it=True, get_output=False)

    def push_branch_to_origin(self, parameters: Iterable[str] = tuple()) -> bool:
        """
        Push do aktualni vetve
        """
        try:
            cmd("git push origin {} {}".format(' '.join(parameters), self.get_current_branch()), print_it=True, get_output=False)
            return True
        except Exception:
            return False

    def reset_hard(self, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> str:
        return cmd("git reset --hard {}".format(self.mute(quiet)), print_it=print_it, get_output=get_output)

    def reset_hard_to_origin(self, quiet: bool = False, print_it: bool =True, get_output: bool =False):
        return cmd("git reset --hard @{{upstream}} {}".format(self.mute(quiet)), print_it=print_it, get_output=get_output)

    def merge_with_master(self, branch: str, quiet: bool = False, print_it: bool = True, get_output: bool = False) -> bool:
        self.co_master(quiet=quiet, print_it=print_it, get_output=get_output)
        try:
            cmd("git merge {} --no-ff --no-edit {}".format(branch, self.mute(quiet)), print_it=print_it, get_output=get_output)
            return True
        except Exception:
            self.reset_hard(quiet=quiet, print_it=print_it, get_output=get_output)
            return False

    def get_repo(self, repository: str, print_it: bool = True, get_output: bool = False) -> Iterable[str]:
        os.chdir(self.root)
        if self.reuse_last_repo and os.path.isdir(os.path.join(self.root, "copy")):
            # Jen velezeme do repa a zresetujeme ho
            os.chdir(os.path.join(self.root, "copy"))
            self.reset_hard()
        else:
            for item in iter_cmd(
                    "git clone --progress {} copy".format(repository),
                    print_it=print_it,
                    get_output=get_output,
                    output_pipe='stderr'):

                yield item
            os.chdir(os.path.join(self.root, "copy"))
        self.co_master(print_it=False, get_output=False)

    def get_current_branch(self) -> bool:
        return cmd("git rev-parse --abbrev-ref HEAD", print_it=False, get_output=True)

    def was_branch_commited(self, branch_name: str) -> bool:
        try:
            cmd("git log {} >/dev/null 2>&1".format(branch_name), print_it=False, get_output=False)
            cmd("git log origin/{} >/dev/null 2>&1".format(branch_name), print_it=False, get_output=False)
        except Exception:
            return False
        return True

    def commit(self, message: str) -> bool:
        try:
            cmd("git commit -m '{}'".format(message), print_it=True, get_output=True)
        except Exception:
            return False
        return True

    def add(self, files: List[str]) -> bool:
        try:
            # add files
            cmd("git add {}".format(' '.join(files)), print_it=True, get_output=False)
        except Exception:
            return False
        return True

    def get_changed_files(self) -> None:
        status = cmd("git status --short | awk '/[M][M]*/{print $NF}'", print_it=False, get_output=True)
        changed_files = status.split('\n')
        return changed_files

    def get_log_messages(self, branch_name: str, since: str, until: str = 'now') -> str:
        """
        Ziska vsechny log zpravy z aktualni vetve od zadaneho datumu.

        Pro omezeni datumu lze pouzivat urcovani casu primo z gitu viz. info:

            http://schacon.github.io/git/gitrevisions.html

        viz. --since a --until.
        """
        return cmd(
            'git log {} --since=\'{}\' --until=\'{}\' --pretty=format:\'%h,%an,%ar,%s\' --'.format(
                branch_name,
                since,
                until
            ),
            print_it=False,
            get_output=True
        )


if __name__ == '__main__':
    git = Git(reuse_last_repo=False)
    git.init_workdir()
    for i in git.get_repo("git@gitlab.kancelar.seznam.cz:sos/k8s-tt-config.git", print_it=False):
        print(i)

    print("Naklonovano do", git.get_copy_dir())
    modifile = "sos-groupware-bridge_deploy.yaml"
    modipath = os.path.join(git.get_copy_dir(), "sos-stable", modifile)
    with open(modipath, "a+") as testf:
        testf.write("xxxx")
    git.add([os.path.join("sos-stable", modifile)])
    git.commit("ppokus")
    git.push_master()


#!/usr/bin/env python3

import json
import praw
import requests
import time


try:
    from config import *  # NOQA
except:
    USERNAME = 'someuser'
    PASSWORD = 'somepass'
    CACHEFILE = '/path/to/cache.file'


class Bot(object):
    def __init__(self, username, password):
        user_agent = '/u/{} running ban_pruner.py'.format(USERNAME)
        self.headers = {'User-Agent': user_agent}
        self.r = praw.Reddit(user_agent)
        self.r.login(username, password)
        self.banned = set()  # list of accounts who are staying banned
        self.unbanned = self.get_ban_list()  # list of accounts already unbanned
        self.sleep_time = 2

    def get_ban_list(self):
        '''Retrieves the unbanned from CACHEFILE.'''

        try:
            with open(CACHEFILE) as f:
                unbanned = set(json.loads(f.read()))
        except (IOError, ValueError):
            unbanned = set()
        return unbanned

    def set_ban_list(self):
        '''Writes unbanned to CACHEFILE.'''

        with open(CACHEFILE, 'w') as f:
            f.write(json.dumps(list(self.unbanned)))

    def accept_mod_invites(self):
        '''Accepts moderator invites.'''

        for message in self.r.get_unread():
            message.mark_as_read()
            # just assume every message in the inbox is a mod-invite
            try:
                self.r.accept_moderator_invite(message.subreddit.display_name)
            except praw.errors.InvalidInvite:
                pass

    def is_shadowbanned(self, username):
        try:
            time.sleep(self.sleep_time)
            u = requests.get(
                'http://reddit.com/user/{}/?limit=1'.format(user.name), headers=self.headers)
        except requests.exceptions.ConnectionError:
            self.sleep_time += 2
            self.is_shadowbanned(username)
        if u.status_code == 404:
            self.sleep_time = 2
            return True
        else:
            return False

    def prune_bans(self, subreddit):
        '''Function that returns names of unbanned users.  The first returned value is
        the intial number of bans.'''

        banned = [i for i in subreddit.get_banned()]
        unbanned = []
        for user in banned:
            if user.name in self.unbanned and user.name not in self.banned:
                subreddit.unban(user)
                unbanned.append(user.name)
            else:
                if self.is_shadowbanned(user.name):
                    subreddit.remove_ban(user.name)
                    self.unbanned.add(user.name)
                    unbanned.append(user.name)
                else:
                    self.banned.add(user.name)
        return len(banned), unbanned

    def process_subreddit(self, subreddit):
        '''Processes the ban list and then messages the moderators the summary.'''

        original_ban_count, unbanned = self.prune_bans(subreddit)
        unbanned_count = len(unbanned)
        bans_left = original_ban_count - unbanned_count
        message = (
            "I've just completed pruning your ban list, so here's a summary of what I've removed:"
            "\n\n{}\n\n   Your subreddit had a total of {} bans. {} of them were shadowbanned or "
            "deleted and were removed from the list.  You now have {} bans.  I have now removed m"
            "yself from your moderator list.  Feel free to re-add me at any time.  If you're sati"
            "fied with the job I've done, please consider leaving feedback at /r/ban_pruner/w/fee"
            "dback.")
        if unbanned_count == 0:
            summary = "* There were no deleted or shadowbanned users removed."
        else:
            summary = "\n\n".join(['1. /u/{}'.format(i) for i in unbanned])
        self.r.send_message(
            subreddit, 'Pruned Bans', message.format(
                summary, original_ban_count, unbanned_count, bans_left))

    def run(self):
        self.accept_mod_invites()
        for subreddit in self.r.get_my_moderation():
            if subreddit.display_name != self.r.user.name:
                self.process_subreddit(subreddit)
                subreddit.remove_moderator(self.r.user.name)
        self.set_ban_list()

if __name__ == '__main__':
    bot = Bot(USERNAME, PASSWORD)
    bot.run()

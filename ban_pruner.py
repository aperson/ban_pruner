#!/usr/bin/env python3

import json
import os
import praw
from praw.handlers import MultiprocessHandler
import requests
import time


try:
    from config import *  # NOQA
except:
    USERNAME = 'someuser'
    PASSWORD = 'somepass'
    BASEDIR = '/some/path/'
    CACHEFILE = '{}/cache.file'.format(BASEDIR)


class Bot(object):
    def __init__(self, username, password):
        user_agent = '/u/{} running ban_pruner.py'.format(USERNAME)
        self.headers = {'User-Agent': user_agent}
        self.r = praw.Reddit(user_agent, handler=MultiprocessHandler())
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

    def write_summary_to_disk(self, path, filename, summary):
        '''Writes summaries to disk.  Creates folders when needed.'''

        full_path = '{}/{}'.format(BASEDIR, path)
        if not os.path.exists(path):
            os.makedirs(path)
        with open('{}/{}'.format(full_path, filename), 'w') as f:
            f.write(summary)

    def accept_mod_invites(self):
        '''Accepts moderator invites.'''

        for message in self.r.get_unread(limit=None):
            message.mark_as_read()
            # just assume every message in the inbox is a mod-invite
            try:
                self.r.accept_moderator_invite(message.subreddit.display_name)
            except praw.errors.InvalidInvite:
                pass

    def is_shadowbanned(self, user):
        print("Checking if /u/{} is shadowbanned or deleted".format(user.name))
        try:
            time.sleep(self.sleep_time)
            u = requests.get(
                'http://reddit.com/user/{}/?limit=1'.format(user), headers=self.headers)
            if u.status_code == 404:
                self.sleep_time = 2
                return True
        except requests.exceptions.ConnectionError:
            self.sleep_time += 2
            self.is_shadowbanned(user)

    def remove_ban(self, subreddit, user):
        try:
            subreddit.remove_ban(user)
        except requests.exceptions.HTTPError:
            pass

    def prune_bans(self, subreddit):
        '''Function that returns names of unbanned users.  The first returned value is
        the intial number of bans.'''

        print("Processing the bans in: {}".format(subreddit.display_name))
        banned = [i for i in subreddit.get_banned(limit=None)]
        unbanned = []
        for user in banned:
            if user.name in self.unbanned and user.name not in self.banned:
                self.remove_ban(subreddit, user)
                unbanned.append(user.name)
            else:
                if self.is_shadowbanned(user):
                    self.remove_ban(subreddit, user)
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
        elif unbanned_count > 200:
            current_time = time.strftime('%Y%m%d')
            path = 'summaries/{}'.format(subreddit.display_name)
            wiki_page = '{}/{}'.format(path, current_time)
            wiki_content = "\n\n".join(['* /u/{}'.format(i) for i in unbanned])
            self.write_summary_to_disk(path, current_time, wiki_content)
            self.r.edit_wiki_page(self.r.user.name, wiki_page, wiki_content)
            summary = "* Full summary can be found at /r/{}/w/{}".format(
                self.r.user.name, wiki_page)
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

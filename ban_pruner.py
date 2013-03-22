#!/usr/bin/env python3

import praw
import requests  # Needed to catch requests.exceptions.HTTPError


try:
    from credentials import *  # NOQA
except:
    USERNAME = 'someuser'
    PASSWORD = 'somepass'


class Bot(object):
    def __init__(self, username, password):
        self.r = praw.Reddit('/u/{} running ban_pruner.py'.format(USERNAME))
        self.r.login(username, password)
        self.unbanned = []  # internal list of people already unbanned

    def accept_mod_invites(self):
        '''Accepts moderator invites.'''

        for message in self.r.get_unread():
            message.mark_as_read()
            # just assume every message in the inbox is a mod-invite
            try:
                r.accept_moderator_invite(message.subreddit.display_name)
            except InvalidInvite:
                pass

    def prune_bans(self, subreddit):
        '''Generator function that returns names of unbanned users.  The first returned value is
        the intial number of bans.'''
        banned = [i for i in subreddit.get_banned()]
        yield len(banned)
        for user in banned:
            if user.name in self.unbanned:
                subreddit.unban(user)
                yield user.name
            else:
                try:
                    user.get_overview().__next__()
                except requests.exceptions.HTTPError:
                    subreddit.remove_ban(user.name)
                    self.unbanned.append(user.name)
                    yield user.name

    def process_subreddit(self, subreddit):
        '''Processes the ban list and then messages the moderators the summary.'''

        unbanned = [i for i in self.prune_bans(subreddit)]

        message = (
            "I've just completed pruning your ban list, so here's a summary of what I've removed:"
            "\n\n{}\n\n   There was a total of {} shadowbanned or deleted users removed.")
        if unbanned[0] == 0:
            summary = ""
        else:
            summary = "\n\n".join(['{}. /u/{}'.format(*i) for i in enumerate(unbanned[1:])])
        self.r.send_message(subreddit, 'Pruned Bans', message.format(summary, unbanned[0]))
        if subreddit.display_name != self.r.user.name:
            subreddit.remove_moderator(self.r.user.name)

    def run(self):
        for subreddit in self.r.get_my_moderation():
            self.process_subreddit(subreddit)

if __name__ == '__main__':
    bot = Bot(USERNAME, PASSWORD)
    bot.run()

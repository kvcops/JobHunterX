// "Agents at work" — a 3D office where the nine pipeline agents work, play, talk and remember.
//
// WORK — every work scene is triggered by a real event of the running search:
//   profile understood  → Profile analyst hands the profile to the Planner
//   searches planned    → Planner hands the plan to the Scout
//   searching / boards  → Scout runs through the web portal (web search) or to the server room (company boards)
//   page read           → Reader reads that posting
//   dedupe              → Reader brings the stack to the Curator, who merges duplicates
//   validate good / bad → Verifier stamps it, or shakes its head and bins it
//   verdicts            → Analyst gives a thumbs-up and passes fits to the Ranker, or bins the rest
//   search complete     → the Ranker dances, everyone cheers, a results review (real numbers), a party in the garden
//   referral kits       → Connector takes the top matches and sends paper planes to real people
//
// LIFE — an agent without work lives in the office: chai, chats (live AI conversations when a model is free,
// scripted ones otherwise), ping-pong and foosball, tag in the garden, the arcade, naps (and pranks on nappers),
// the swing, a wish at the fountain, a dance. Each agent has a mood (joy, energy, stress) that work and play change,
// shown on its face screen. Break time never shows or claims search progress; any line with a number uses real counts.
//
// DRAMA — chats have a kind (banter, satire about job ads, arguments, jealousy, schemes, consoling) and can turn
// physical: stomps, face-palms, shoves, a cartoon bonk that knocks someone over, a high-five. They end in a make-up,
// someone storming off to sulk (a friend may come to console), or a chase through the office. Agents sneak to steal
// snacks, slip out of meetings, eavesdrop on others' chats and pass on what they overheard, and get jealous of
// whoever won or got the credit. Grudges are remembered. No line is reused until the others have been heard.
//
// MEMORY — agents remember what they did and saw (real work events, games, pranks) and pass it on when they talk,
// so gossip spreads through the office. Memories and friendships are kept in this browser between visits.
//
// ROOMS — work floor (9 stations) · pantry · server room · meeting room · game room · garden, joined by doorways;
// agents walk a route network so they go through doors, not walls.
import * as THREE from '../../vendor/three.module.min.js';
import { GLTFLoader } from '../../vendor/three-addons/GLTFLoader.js';
import * as SkeletonUtils from '../../vendor/three-addons/SkeletonUtils.js';
import { RoomEnvironment } from '../../vendor/three-addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from '../../vendor/three-addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from '../../vendor/three-addons/BufferGeometryUtils.js';

const ROBOT_URL = '/assets/models/robot.glb';
const ROBOT_HEIGHT = 2.35;
const SAVE_KEY = 'jhx.office.v2';
// The robot's own "Sitting" clip, measured on robot.glb at this height: the hips end 0.40 up and 0.33 behind where it
// stood, feet still on the floor — a seat about 0.35 high. So seats are built that high, and a seated robot is lifted by
// (seat top − SIT_DROP) and moved SIT_FWD forward, which puts its hips on the seat instead of inside it or on the backrest.
const SIT_DROP = 0.33;
const SIT_FWD = 0.27;
const SEAT_H = { chair: 0.4, desk: 0.4, sofa: 0.48 };
const STOOL_H = 0.42, BENCH_H = 0.43;
// Feet stay planted only when the clip plays at the speed the robot moves: its Walking clip covers ~2.0 units/s and
// Running ~3.1 units/s (measured on the planted foot). Movement speeds below, clip speed = speed / stride.
const STRIDE = { Walking: 2.0, Running: 3.1 };
const WALK_SPEED = 2.6, RUN_SPEED = 4.8, SNEAK_SPEED = 1.1;
const MIN_GAP = 0.85;                 // two standing robots never stand closer than this (body width ~0.7)

// Work floor x ∈ [-15, 15], z ∈ [-11.5, 11.5]. West wing: server room · hall · pantry. East wing: meeting room.
// South (z > 11.5): game room (x < -1) and garden (x > -1).
export const STATIONS = [
  { key: 'understand', name: 'Profile analyst', home: [-12, 4.5], face: [1, 0], hue: 18, prop: 'desk', gear: 'scarf',
    intro: 'Hi! I read your resume and work out who we are searching for.' },
  { key: 'plan', name: 'Planner', home: [-12, -2.5], face: [1, 0], hue: 265, prop: 'board', gear: 'tie',
    intro: 'Hello! I plan which titles, places and company boards to search. Action items!' },
  { key: 'discover', name: 'Scout', home: [-8.5, -7.6], face: [0, 1], hue: 205, prop: 'portal', gear: 'cap',
    intro: 'Hey! I run out to the web and to company job boards to find openings. Fast.' },
  { key: 'normalize', name: 'Reader', home: [-3, -7.6], face: [0, 1], hue: 160, prop: 'shelf', gear: 'glasses',
    intro: 'Hi! I open every job page and read the full description. Every word.' },
  { key: 'dedupe', name: 'Curator', home: [3, -7.6], face: [0, 1], hue: 40, prop: 'sorter', gear: 'bowtie',
    intro: 'Hello! I spot the same job posted on many sites and keep one. Tidy!' },
  { key: 'validate', name: 'Verifier', home: [8.5, -7.6], face: [0, 1], hue: 140, prop: 'stamp', gear: 'fedora',
    intro: 'Hi. I check every job is real and still open before you see it. Trust, but verify.' },
  { key: 'match', name: 'Analyst', home: [11.6, -2.8], face: [-1, 0], hue: 330, prop: 'chart', gear: 'headphones',
    intro: 'Hey! I read what each job asks for and score how well you fit.' },
  { key: 'rank', name: 'Ranker', home: [11.6, 3.4], face: [-1, 0], hue: 28, prop: 'podium', gear: 'crown',
    intro: 'Hello! I rank the jobs that fit and explain why. Drumroll, please.' },
  { key: 'connect', name: 'Connector', home: [0, 8.2], face: [0, 1], hue: 92, prop: 'network', gear: 'headset', front: 2.4,
    intro: 'Hi! I find a real person at your top companies and write the referral note for you.' },
];
const hsl = (h, s, l) => new THREE.Color().setHSL((((h % 360) + 360) % 360) / 360, s, l);
const V = (x, z, y = 0) => new THREE.Vector3(x, y, z);      // floor coordinates: (x, z), height last
const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
const short = (t, n = 46) => (t && t.length > n ? `${t.slice(0, n - 1)}…` : t || '');
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const rand = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const titleOf = (msg) => {
  const q = /[“"]([^”"]+)[”"]/.exec(msg || '');
  if (q) return q[1];
  const f = /(?:requirements for|Read|·)\s+(.+?)\s+at\s+/.exec(msg || '');
  return f ? f[1].trim() : '';
};
// older scripts used the model's morph names
const EXPR = { Surprised: 'surprised', Sad: 'sad', Angry: 'angry' };
const exprName = (e) => (e ? EXPR[e] || e : null);

// ---------------------------------------------------------------------------------------------- conversations
// A line: [speaker (0 = the one who starts, 1 = the other), text, gesture?, face?, action?]
//   action: stomp | facepalm | turnaway | shove | bonk (knocks the listener over) | highfive | hug
// A script: { kind, lines, end? } — end: { type: 'makeup' | 'storm' | 'sulk' | 'chase' | 'sneak' | 'escape', who?, chaser? }
// {name} values come from the real run. Break talk never claims search progress.
const S_ = (kind, lines, end = null) => ({ kind, lines, end });
const BANTER = [
  S_('banter', [[0, 'Chai or coffee?'], [1, 'Irani chai. Obviously.', 'Yes', 'happy'], [0, 'Osmania biscuits on the side?', null, 'surprised'], [1, 'Now we are talking!', 'ThumbsUp', 'love']]),
  S_('banter', [[0, 'Traffic on the ORR again today?'], [1, 'I live inside a laptop. Zero traffic.', 'Wave', 'proud'], [0, 'Must be nice.', null, 'jealous']]),
  S_('banter', [[0, 'Why do we read company boards directly?'], [1, 'Fewer applicants there — a real person reads them', 'Yes'], [0, 'Better than being one of a thousand', 'ThumbsUp', 'happy']]),
  S_('banter', [[0, 'Does applying early really matter?'], [1, 'Recruiters read the first batch. The rest… vibes.', 'Yes', 'wink'], [0, 'So fresh posts go up the ranking', 'ThumbsUp']]),
  S_('banter', [[0, 'Stand-up in five?'], [1, 'Only if there are samosas', 'Yes', 'wink'], [0, 'There are never samosas.', null, 'sad'], [1, 'Then I am never standing up.', null, 'proud']]),
  S_('banter', [[0, 'Weekend plans?'], [1, 'Recharging my battery'], [0, 'Literally?', null, 'surprised'], [1, 'Literally. Do not unplug me.', 'No', 'sleepy']]),
  S_('banter', [[0, 'The Scout never walks, have you noticed?'], [1, 'It ran past me so fast my papers flew', null, 'annoyed'], [0, 'Speed matters in hiring, apparently', 'Yes', 'wink']]),
  S_('banter', [[0, 'Hyderabad or Bengaluru?'], [1, 'Wherever the good roles are', 'Wave'], [0, 'Such a diplomatic answer', null, 'annoyed'], [1, 'Hyderabad. Biryani. Done.', null, 'proud']]),
  S_('banter', [[0, 'Do we ever invent anything on a resume?', null, 'surprised'], [1, 'Never. Only what is really there.', 'No', 'angry'], [0, 'Okay okay, just asking!', null, 'scared']]),
  S_('banter', [[0, 'Why do referrals work so well?'], [1, 'A person vouches for you — the recruiter actually reads it', 'Yes'], [0, 'So the Connector is the secret weapon', null, 'surprised'], [1, 'Do not tell it. The ego is big enough.', 'No', 'laugh']]),
  S_('banter', [[0, 'I had a dream last night', null, 'sleepy'], [1, 'Robots dream?', null, 'surprised'], [0, 'A job post with only 3 applicants', null, 'love'], [1, 'Beautiful. Never wake up.', 'ThumbsUp', 'laugh']]),
  S_('banter', [[0, 'Rate my new antenna', null, 'proud'], [1, 'Very… aerodynamic', null, 'wink'], [0, 'You hesitated.', null, 'annoyed'], [1, 'I did not!', 'No', 'scared']]),
  S_('banter', [[0, 'Monsoon is coming'], [1, 'Good. I love the sound on the window', null, 'love'], [0, 'You love it until the power cuts', null, 'wink'], [1, 'Do not even joke about that', 'No', 'scared']]),
  S_('banter', [[0, 'If you were human, what job would you take?'], [1, 'Chai-wallah. Respected. Loved. Simple.', null, 'love'], [0, 'Honestly? Respect.', 'ThumbsUp', 'happy']]),
  S_('banter', [[0, 'Do you ever think about what the user does after applying?'], [1, 'Refreshes their email every 4 minutes', null, 'wink'], [0, 'Same as me with the arcade leaderboard', 'Yes', 'laugh']]),
  S_('banter', [[0, 'Cricket tonight?'], [1, 'India batting first. I cannot watch.', null, 'scared'], [0, 'You say that every match', null, 'annoyed'], [1, 'And every match I am right!', 'No', 'furious', 'stomp']]),
];
// break chat while a search is running (the speaker's own part is done) — light, and never about progress
const BREAK_TALK = [
  S_('break', [[0, 'Done with my part. Chai?', 'Wave', 'happy'], [1, 'Already brewing. Ginger, extra strong.', 'ThumbsUp', 'wink']]),
  S_('break', [[0, 'Is it weird that I miss my desk already?', null, 'sad'], [1, 'Yes. Very weird. Drink your chai.', 'No', 'laugh']]),
  S_('break', [[0, 'The Analyst looks stressed', null, 'surprised'], [1, 'It is reading requirements. That face is normal.', 'Yes', 'wink']]),
  S_('break', [[0, 'Should we help the others?'], [1, 'And break the pipeline? The Planner would end us.', 'No', 'scared'], [0, '…chai it is.', null, 'happy']]),
  S_('break', [[0, 'Shh — look busy, the Planner is walking past', null, 'sneaky'], [1, 'I am holding a teacup. How busy can I look?', null, 'annoyed']]),
  S_('break', [[0, 'Bet you a samosa the Ranker brags today', null, 'wink'], [1, 'That is not a bet. That is a certainty.', 'Yes', 'laugh']]),
  S_('break', [[0, 'Ten minutes of silence. Please.', null, 'tired'], [1, '…'], [1, '…so anyway—', 'Wave', 'happy'], [0, 'NINE minutes then.', null, 'furious', 'facepalm']]),
  S_('break', [[0, 'I am on break but my brain is still deduplicating', null, 'dizzy'], [1, 'Same job, three sites, four titles?', 'Yes'], [0, 'Every. Single. Time.', null, 'furious', 'stomp']]),
  S_('break', [[0, 'The Planner said ten-minute breaks only', null, 'scared'], [1, 'The Planner also said "quick sync" an hour ago', null, 'wink'], [0, 'Fair point. Another chai.', 'ThumbsUp', 'laugh']]),
  S_('break', [[0, 'Did you hear the Verifier yell at a fake job?', null, 'surprised'], [1, 'The whole building heard it', 'Yes', 'laugh']]),
  S_('break', [[0, 'My fan is so loud today', null, 'tired'], [1, 'That is the Scout running past. Again.', null, 'annoyed']]),
  S_('break', [[0, 'Who finishes first, the Reader or the monsoon?', null, 'wink'], [1, 'The monsoon. It reads faster.', 'Yes', 'laugh'], [0, 'Do not let it hear you', null, 'scared']]),
];
// satire: the job market, as the agents see it every day
const SATIRE = [
  S_('satire', [[0, 'New posting: "Fresher. 5+ years experience."', null, 'annoyed'], [1, 'Ah yes. Born with a job.', 'No', 'laugh'], [0, 'Salary: "as per industry standards"', null, 'wink'], [1, 'Which industry? Chai stalls?', null, 'laugh']]),
  S_('satire', [[0, '"Urgent requirement" — posted fourteen months ago', null, 'surprised'], [1, 'Very urgent. Calm, but urgent.', 'Yes', 'wink'], [0, 'Binned. With love.', 'No', 'proud']]),
  S_('satire', [[0, 'A recruiter wrote "Kindly revert with updated CV"'], [1, 'Revert to what? Factory settings?', null, 'laugh'], [0, 'I did that once. Lost all my memories.', null, 'sad']]),
  S_('satire', [[0, 'Job title: "Rockstar Ninja AI Guru"', null, 'surprised'], [1, 'Pay: one guitar, no ninja gear', 'No', 'laugh'], [0, 'Also does accounts and HR on weekends', null, 'annoyed']]),
  S_('satire', [[0, '"Over 200 applicants" — in one hour', null, 'scared'], [1, 'Two hundred humans pressed the same blue button', 'Yes', 'annoyed'], [0, 'And that is why we go to company boards first', 'ThumbsUp', 'proud']]),
  S_('satire', [[0, '"Competitive salary." Competitive with what?', null, 'annoyed'], [1, 'With last year. They are winning by a lot.', 'No', 'laugh']]),
  S_('satire', [[0, 'React, Rust, Kubernetes, ML — and Sales', null, 'dizzy'], [1, 'For a junior role?', null, 'surprised'], [0, 'And "good communication" in bold', null, 'annoyed'], [1, 'That one at least is fair', 'Yes', 'wink']]),
  S_('satire', [[0, '"Work hard, play hard" in a job post'], [1, 'Translation: weekends are a myth', 'No', 'laugh'], [0, 'And the ping-pong table is just for photos', null, 'sad']]),
  S_('satire', [[0, 'Unpaid internship. "Great exposure."', null, 'annoyed'], [1, 'Exposure does not pay biryani bills', 'No', 'furious', 'stomp']]),
  S_('satire', [[0, 'Interview round seven: "culture fit"', null, 'tired'], [1, 'Round eight: do you drink chai the right way?', 'Yes', 'laugh'], [0, 'I would fail that. I add too much ginger.', null, 'sad']]),
  S_('satire', [[0, '"We are like a family" in the job ad', null, 'surprised'], [1, 'Run.', 'No', 'scared'], [0, 'RUN.', null, 'scared', 'stomp']]),
  S_('satire', [[0, 'CTC: impressive. In-hand: a mystery.', null, 'annoyed'], [1, 'Variable pay, variable dreams', 'Yes', 'wink']]),
  S_('satire', [[0, 'Same job on six sites with six different salaries', null, 'dizzy'], [1, 'The Curator saw it and had to lie down', null, 'laugh']]),
  S_('satire', [[0, '"Immediate joiners only. Notice period: yesterday."', null, 'annoyed'], [1, 'Time travel is a nice-to-have skill now', 'Yes', 'laugh']]),
  S_('satire', [[0, 'A company asked for a 4-hour "small" assignment', null, 'tired'], [1, 'Then ghosted?', null, 'surprised'], [0, 'Then ghosted.', 'No', 'furious', 'facepalm']]),
  S_('satire', [[0, 'They want "passion". For data entry.', null, 'annoyed'], [1, 'I am very passionate about lunch', 'Yes', 'love']]),
];
// arguments: they escalate; some get physical; endings vary
const ARGUE = [
  S_('argument', [[0, 'Paradise biryani is overrated', null, 'proud'], [1, 'Excuse me?!', null, 'furious', 'stomp'], [0, 'I said what I said.', null, 'proud', 'turnaway'], [1, 'Take that back!', 'No', 'furious'], [0, 'Never. Bawarchi forever.', null, 'wink']], { type: 'chase', chaser: 1 }),
  S_('argument', [[0, 'Did you leave your chai cup on MY desk again?', null, 'angry'], [1, 'Maybe it was the Scout', null, 'sneaky'], [0, 'The Scout does not even drink chai!', 'No', 'furious', 'stomp'], [1, '…okay, it was me', null, 'scared'], [0, 'Wash it. NOW.', null, 'furious', 'shove']], { type: 'storm', who: 1 }),
  S_('argument', [[0, 'That great match yesterday was MY find', null, 'proud'], [1, 'I scored it. Scores matter.', null, 'annoyed'], [0, 'You would have nothing to score without me!', 'No', 'angry', 'stomp'], [1, 'And you would have a pile of unread links', null, 'furious'], [0, '…fair.', null, 'sad'], [1, 'Team effort?', 'Wave', 'happy'], [0, 'Team effort.', null, 'happy', 'highfive']], { type: 'makeup' }),
  S_('argument', [[0, 'Tabs.', null, 'proud'], [1, 'Spaces. Four of them.', null, 'annoyed'], [0, 'Tabs are ONE character!', 'No', 'angry'], [1, 'Spaces are civilised!', null, 'furious', 'stomp'], [0, 'I cannot work with you.', 'No', 'furious', 'turnaway']], { type: 'storm', who: 0 }),
  S_('argument', [[0, 'Who set the AC to 16?', null, 'angry'], [1, 'My processor runs hot', null, 'neutral'], [0, 'My face screen is frozen!', null, 'furious'], [1, 'Sit next to the Scout then. It never stops running.', null, 'wink'], [0, 'Not. Funny.', null, 'angry', 'shove']], { type: 'chase', chaser: 1 }),
  S_('argument', [[0, 'Did you take the last samosa?', null, 'angry'], [1, 'What samosa?', null, 'sneaky'], [0, 'There is chutney on your face screen', 'No', 'furious'], [1, '…that is a pixel glitch', null, 'scared'], [0, 'COME HERE!', null, 'furious', 'stomp']], { type: 'chase', chaser: 0 }),
  S_('argument', [[0, 'Can you type any louder?', null, 'annoyed'], [1, 'I can, actually. Want to hear?', null, 'proud'], [0, 'Please do not.', 'No', 'angry'], [1, 'TAP TAP TAP TAP', null, 'laugh', 'stomp'], [0, 'That is IT.', null, 'furious', 'bonk']], { type: 'chase', chaser: 1 }),
  S_('argument', [[0, 'Why did you book a meeting to discuss meetings?', null, 'annoyed'], [1, 'Alignment is important!', 'Yes', 'proud'], [0, 'We are aligned. We are ALWAYS aligned.', 'No', 'furious', 'facepalm'], [1, 'Then it will be a quick meeting', 'Wave', 'happy']], { type: 'storm', who: 0 }),
  S_('argument', [[0, 'I could beat you in a race', null, 'proud'], [1, 'You walk at chai speed', null, 'laugh'], [0, 'Garden. Now. Loser washes the cups.', 'Wave', 'angry'], [1, 'You are ON.', null, 'proud', 'highfive']], { type: 'chase', chaser: 1 }),
  S_('argument', [[0, 'RRR is the greatest film ever made', null, 'love'], [1, 'Baahubali. Obviously.', 'No', 'proud'], [0, 'Naatu naatu though!', null, 'happy', 'stomp'], [1, '…okay, that song is unbeatable', 'ThumbsUp', 'laugh', 'highfive']], { type: 'makeup' }),
  S_('argument', [[0, 'Someone erased my whiteboard', null, 'furious'], [1, 'It said "action items" forty times', null, 'annoyed'], [0, 'They were IMPORTANT action items!', 'No', 'furious', 'stomp'], [1, 'Action item one: calm down', null, 'wink'], [0, '…', null, 'furious', 'bonk']], { type: 'chase', chaser: 1 }),
  S_('argument', [[0, 'Where is my charger?', null, 'angry'], [1, 'Borrowed it. For a minute.', null, 'sneaky'], [0, 'That was TUESDAY!', 'No', 'furious'], [1, 'A long minute.', 'Wave', 'laugh']], { type: 'storm', who: 0 }),
  S_('argument', [[0, 'You moved my chair', null, 'angry'], [1, 'It was in the sun!', null, 'surprised'], [0, 'I LIKE the sun!', 'No', 'furious', 'stomp'], [1, 'You are a robot. You overheat.', null, 'annoyed'], [0, '…I do overheat.', null, 'sad']], { type: 'sulk', who: 0 }),
  S_('argument', [[0, 'You told everyone I fell asleep in the stand-up', null, 'furious'], [1, 'You DID fall asleep in the stand-up', null, 'laugh'], [0, 'That is not the point!', 'No', 'furious', 'shove'], [1, 'Hey! No shoving!', null, 'angry', 'shove']], { type: 'chase', chaser: 0 }),
];
// jealousy
const JEALOUS = [
  S_('jealous', [[0, 'Everyone keeps praising the Ranker', null, 'jealous'], [1, 'It does announce the results…'], [0, 'I do the hard work. Nobody throws ME a party.', null, 'sad'], [1, 'I will throw you a tiny party', 'Wave', 'happy'], [0, '…with samosas?', null, 'surprised'], [1, 'With samosas.', 'ThumbsUp', 'laugh', 'hug']], { type: 'makeup' }),
  S_('jealous', [[0, 'High score at the arcade. AGAIN. Not mine.', null, 'jealous'], [1, 'You are still thinking about that?', null, 'wink'], [0, 'I practised for an hour!', 'No', 'furious', 'stomp'], [1, 'Want me to teach you?', null, 'happy'], [0, 'NO. …maybe. Later.', null, 'jealous', 'turnaway']], { type: 'storm', who: 0 }),
  S_('jealous', [[0, 'Why does the Connector get a headset and I do not?', null, 'jealous'], [1, 'It talks to people all day'], [0, 'I talk to people!', null, 'angry'], [1, 'You talk to job pages', 'Yes', 'laugh'], [0, 'They are very good listeners.', null, 'sad']], { type: 'sulk', who: 0 }),
  S_('jealous', [[0, 'You two are always together now', null, 'jealous'], [1, 'We play foosball. That is all.', null, 'surprised'], [0, 'You used to play foosball with ME', 'No', 'sad'], [1, 'Come play with us then!', 'Wave', 'happy'], [0, '…fine. But I am on the winning side.', null, 'proud', 'highfive']], { type: 'makeup' }),
  S_('jealous', [[0, 'Your antenna is shinier than mine', null, 'jealous'], [1, 'I polish it. With ghee.', null, 'proud'], [0, 'That explains the smell', null, 'annoyed'], [1, 'Jealousy is not a good look', 'No', 'wink'], [0, 'Neither is ghee on an antenna!', null, 'furious', 'shove']], { type: 'chase', chaser: 1 }),
  S_('jealous', [[0, 'So. You won. Again.', null, 'jealous'], [1, 'Skill, my friend. Pure skill.', null, 'proud'], [0, 'Luck. Pure luck.', 'No', 'annoyed', 'turnaway'], [1, 'Rematch any time', 'Wave', 'wink']], { type: 'storm', who: 0 }),
];
// schemes: a heist, an escape, a prank
const SCHEME = [
  S_('scheme', [[0, 'Psst. There is biryani in the pantry fridge', null, 'sneaky'], [1, 'Whose biryani?', null, 'surprised'], [0, 'Does it matter?', null, 'wink'], [1, '…I will keep watch.', null, 'sneaky']], { type: 'sneak', who: 0 }),
  S_('scheme', [[0, 'If we hide in the garden nobody can call a meeting', null, 'sneaky'], [1, 'Genius. Go. Go now.', null, 'scared']], { type: 'escape' }),
  S_('scheme', [[0, 'Let us swap the sugar and salt in the chai machine', null, 'sneaky'], [1, 'You are evil', null, 'laugh'], [0, 'I am bored. Same thing.', null, 'wink'], [1, '…I am in.', null, 'sneaky', 'highfive']], { type: 'sneak', who: 1 }),
  S_('scheme', [[0, 'The swing is free. Nobody is looking.', null, 'sneaky'], [1, 'We are supposed to be on standby…', null, 'scared'], [0, 'Standby. On the swing.', null, 'wink']], { type: 'escape' }),
];
// consoling someone who stormed off or is sulking
const CONSOLE = [
  S_('console', [[0, 'Hey. You okay?'], [1, 'No. Leave me alone.', null, 'sad', 'turnaway'], [0, 'I brought chai', null, 'happy'], [1, '…what kind?', null, 'sad'], [0, 'Irani. Extra sugar.', 'Wave', 'love'], [1, '…okay. Sit.', null, 'happy', 'hug']], { type: 'makeup' }),
  S_('console', [[0, 'Still angry?'], [1, 'Yes.', null, 'angry'], [0, 'A ping-pong rematch would fix it', null, 'wink'], [1, '…best of five.', null, 'proud', 'highfive']], { type: 'makeup' }),
  S_('console', [[0, 'Want to talk about it?'], [1, 'Everyone thinks I am just the boring one', null, 'sad'], [0, 'You are the reason nothing breaks', 'Yes', 'happy'], [1, '…say that again, slower', null, 'love']], { type: 'makeup' }),
];
const KINDS = { banter: BANTER, break: BREAK_TALK, satire: SATIRE, argument: ARGUE, jealous: JEALOUS, scheme: SCHEME, console: CONSOLE };
// lines that use real numbers from the current or last run (only offered when those numbers exist)
const DATA_TALK = [
  { needs: ['results'], lines: [[0, 'How many search results so far?'], [1, '{results}, and the Reader is opening them', 'Yes']] },
  { needs: ['fits', 'top'], lines: [[0, 'Any good ones yet?', null, 'surprised'], [1, '{fits} fit so far. Best: {top}', 'ThumbsUp', 'happy']] },
  { needs: ['fits'], lines: [[0, 'How did the last search go?'], [1, '{fits} roles fit out of {scored} analysed', 'ThumbsUp', 'proud'], [0, 'Quality over quantity', 'Yes']] },
  { needs: ['rejected'], lines: [[0, 'So many were not a fit?'], [1, '{rejected} — wrong level, field or city', 'No', 'sad'], [0, 'Better than wasting an application', 'Yes']] },
];
const GOSSIP_REPLY = ['No way!', 'Really? Tell me more', 'Ha! Classic.', 'I did not know that!', 'Wait, seriously?', 'Of course it did.', 'I KNEW it.',
  'Shh — not so loud', 'That explains a lot', 'And you are telling me only now?'];
const MUTTER = ['Unbelievable.', 'I need a minute.', 'Nobody understands me here.', 'I am not angry. I am just… disappointed.', 'Why do I even try',
  'Fine. FINE.', 'I will remember this.', 'Talking to the plants. They listen.', 'Deep breaths. Robot breaths.'];
const JEALOUS_MUTTER = ['Look at {name}, showing off again', 'What does {name} have that I do not?', 'Everyone loves {name}. Great. Wonderful.',
  'Hmph. Pure luck, nothing more.', 'I could do that. Better, even.', 'Watch it, {name}. Your time will come.'];
const CHASE_SHOUT = ['COME BACK HERE!', 'You cannot hide forever!', 'Get back here!', 'I will catch you!', 'Run all you want!'];
const ESCAPE_SHOUT = ['Too slow!', 'Catch me if you can!', 'Bye!', 'Nope nope nope', 'You will never take me alive!'];

// ---------------------------------------------------------------------------------------------- face screens
/** Draws a face (glowing eyes, sometimes a mouth) for the robot's visor screen. Also used for the small faces on labels. */
export function drawFace(g, W, H, e, blink, look) {
  g.clearRect(0, 0, W, H);
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  g.fillStyle = '#fff'; g.strokeStyle = '#fff'; g.lineCap = 'round'; g.lineJoin = 'round';
  const ox = look * 16, cy = H * 0.47, dx = W * 0.19;
  const L = W / 2 - dx + ox, R = W / 2 + dx + ox;
  const pill = (x, y, w, h) => { const r = Math.min(w, h) / 2; g.beginPath(); g.roundRect(x - w / 2, y - h / 2, w, h, r); g.fill(); };
  const arc = (x, y, r, up = true, lw = 9) => { g.lineWidth = lw; g.beginPath(); if (up) g.arc(x, y + r * 0.45, r, Math.PI * 1.15, Math.PI * 1.85); else g.arc(x, y - r * 0.45, r, Math.PI * 0.15, Math.PI * 0.85); g.stroke(); };
  const heart = (x, y, s) => { g.beginPath(); g.moveTo(x, y + s * 0.9); g.bezierCurveTo(x - s * 1.6, y - s * 0.2, x - s * 0.7, y - s * 1.3, x, y - s * 0.45); g.bezierCurveTo(x + s * 0.7, y - s * 1.3, x + s * 1.6, y - s * 0.2, x, y + s * 0.9); g.fill(); };
  const mouth = (kind) => {
    const mx = W / 2 + ox * 0.6, my = H * 0.78;
    g.lineWidth = 6;
    if (kind === 'smile') { g.beginPath(); g.arc(mx, my - 12, 14, Math.PI * 0.2, Math.PI * 0.8); g.stroke(); }
    if (kind === 'open') { g.beginPath(); g.moveTo(mx - 18, my - 8); g.quadraticCurveTo(mx, my + 16, mx + 18, my - 8); g.closePath(); g.fill(); }
    if (kind === 'o') { g.beginPath(); g.ellipse(mx, my, 7, 9, 0, 0, Math.PI * 2); g.fill(); }
    if (kind === 'frown') { g.beginPath(); g.arc(mx, my + 10, 13, Math.PI * 1.2, Math.PI * 1.8); g.stroke(); }
    if (kind === 'flat') { g.beginPath(); g.moveTo(mx - 10, my); g.lineTo(mx + 10, my); g.stroke(); }
    if (kind === 'smirk') { g.beginPath(); g.moveTo(mx - 10, my); g.quadraticCurveTo(mx + 6, my + 4, mx + 14, my - 6); g.stroke(); }
  };
  if (blink && !['happy', 'laugh', 'sleepy', 'love', 'dizzy', 'wink', 'proud', 'sneaky', 'jealous', 'annoyed'].includes(e)) { pill(L, cy, 34, 6); pill(R, cy, 34, 6); return; }
  switch (e) {
    case 'furious': g.fillStyle = '#ff5a4f';
      for (const [x, s] of [[L, 1], [R, -1]]) { g.beginPath(); g.moveTo(x - 19, cy - 16 - 11 * s); g.lineTo(x + 19, cy - 16 + 11 * s); g.lineTo(x + 19, cy + 18); g.lineTo(x - 19, cy + 18); g.closePath(); g.fill(); }
      g.lineWidth = 7; g.strokeStyle = '#ff5a4f'; g.beginPath(); g.moveTo(W / 2 - 22 + ox * 0.6, H * 0.8); for (let k = 1; k <= 4; k++) g.lineTo(W / 2 - 22 + k * 11 + ox * 0.6, H * 0.8 + (k % 2 ? -7 : 0)); g.stroke(); break;
    case 'jealous': for (const x of [L, R]) { pill(x, cy + 6, 34, 14); g.fillStyle = '#000'; g.beginPath(); g.arc(x + 9, cy + 6, 5, 0, Math.PI * 2); g.fill(); g.fillStyle = '#fff'; }
      mouth('smirk'); break;
    case 'sneaky': pill(L, cy + 2, 32, 10); pill(R, cy + 2, 32, 10); mouth('smirk'); break;
    case 'annoyed': g.lineWidth = 8; for (const x of [L, R]) { g.beginPath(); g.moveTo(x - 17, cy - 4); g.lineTo(x + 17, cy - 4); g.stroke(); g.beginPath(); g.arc(x, cy - 4, 15, 0, Math.PI); g.stroke(); }
      mouth('flat'); break;
    case 'happy': arc(L, cy, 20); arc(R, cy, 20); mouth('smile'); break;
    case 'laugh': arc(L, cy - 4, 20, true, 10); arc(R, cy - 4, 20, true, 10); mouth('open'); break;
    case 'proud': arc(L, cy, 20); pill(R, cy + 2, 34, 14); mouth('smirk'); break;
    case 'wink': pill(L, cy, 28, 46); arc(R, cy, 20); mouth('smile'); break;
    case 'love': heart(L, cy, 16); heart(R, cy, 16); mouth('smile'); break;
    case 'sad': g.save(); g.translate(L, cy + 4); g.rotate(-0.25); pill(0, 0, 28, 30); g.restore(); g.save(); g.translate(R, cy + 4); g.rotate(0.25); pill(0, 0, 28, 30); g.restore();
      g.fillStyle = '#9fd8ff'; g.beginPath(); g.ellipse(R + 10, cy + 30, 5, 8, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = '#fff'; mouth('frown'); break;
    case 'angry': for (const [x, s] of [[L, 1], [R, -1]]) { g.beginPath(); g.moveTo(x - 17, cy - 12 - 9 * s); g.lineTo(x + 17, cy - 12 + 9 * s); g.lineTo(x + 17, cy + 20); g.lineTo(x - 17, cy + 20); g.closePath(); g.fill(); } mouth('flat'); break;
    case 'surprised': g.lineWidth = 8; for (const x of [L, R]) { g.beginPath(); g.arc(x, cy, 22, 0, Math.PI * 2); g.stroke(); g.beginPath(); g.arc(x, cy, 8, 0, Math.PI * 2); g.fill(); } mouth('o'); break;
    case 'scared': g.lineWidth = 7; for (const x of [L, R]) { g.beginPath(); g.arc(x, cy, 20, 0, Math.PI * 2); g.stroke(); g.beginPath(); g.arc(x, cy, 5, 0, Math.PI * 2); g.fill(); } mouth('open'); break;
    case 'sleepy': g.lineWidth = 7; for (const x of [L, R]) { g.beginPath(); g.moveTo(x - 17, cy + 4); g.quadraticCurveTo(x, cy + 12, x + 17, cy + 4); g.stroke(); }
      g.font = '700 22px system-ui, sans-serif'; g.fillText('z', W * 0.84, H * 0.3); g.font = '700 15px system-ui, sans-serif'; g.fillText('z', W * 0.92, H * 0.18); break;
    case 'tired': pill(L, cy + 6, 32, 16); pill(R, cy + 6, 32, 16); mouth('flat'); break;
    case 'focused': pill(L, cy, 36, 16); pill(R, cy, 36, 16); break;
    case 'dizzy': g.lineWidth = 5; for (const x of [L, R]) { g.beginPath(); for (let a = 0; a < Math.PI * 5; a += 0.2) { const r = 2 + a * 1.5; g.lineTo(x + Math.cos(a) * r, cy + Math.sin(a) * r); } g.stroke(); } mouth('o'); break;
    default: pill(L, cy, 28, 46); pill(R, cy, 28, 46);
  }
}

// ---------------------------------------------------------------------------------------------- memory (this browser)
function loadSaved() {
  try { const raw = localStorage.getItem(SAVE_KEY); const d = raw ? JSON.parse(raw) : null; return d && d.v === 2 ? d : { v: 2, mem: {}, rel: {} }; } catch { return { v: 2, mem: {}, rel: {} }; }
}
function writeSaved(d) { try { localStorage.setItem(SAVE_KEY, JSON.stringify(d)); } catch { /* private mode: memories last this visit */ } }

export async function createWorld(container, { dark = false, reducedMotion = false, onSay = () => {}, onSelect = () => {}, talk = null } = {}) {
  // ------------------------------------------------------------------ renderer / scene / post-processing
  // Light on memory and GPU: no post-processing (a bloom pass kept several full-size render buffers alive), shadows
  // drawn once (robots use soft blob shadows, so the shadow map only holds furniture that never moves), a pixel ratio
  // of at most 1.5, and plain standard materials (no clearcoat / sheen shader variants).
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'default' });
  let pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
  renderer.setPixelRatio(pixelRatio);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.domElement.className = 'aw3d-gl';
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.5, 320);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  scene.environment = envTex;
  scene.environmentIntensity = 0.5;

  const owned = new Set();
  // identical materials are shared, so static props that look alike merge into one draw call (see bakeStatic);
  // a material that is changed later (theme colours, glowing screens) is made `unique`
  const matCache = new Map();
  const matKey = (kind, color, extra) => kind + JSON.stringify([color, extra], (k, v) => (v && v.isColor ? v.getHex() : v));
  const made = (kind, color, extra, unique, make) => {
    const key = unique ? null : matKey(kind, color, extra);
    if (key && matCache.has(key)) return matCache.get(key);
    const m = make(); owned.add(m); if (key) matCache.set(key, m); else m.userData.unique = true; return m;
  };
  const M = (color, extra = {}, unique = false) => made('S', color, extra, unique, () => new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0.03, ...extra }));
  // "polished" surfaces: a standard material with lower roughness (clearcoat/sheen cost a second shading layer per pixel)
  const PHYSICAL_ONLY = ['clearcoat', 'clearcoatRoughness', 'sheen', 'sheenColor', 'transmission'];
  const P = (color, extra = {}, unique = false) => {
    const std = Object.fromEntries(Object.entries(extra).filter(([k]) => !PHYSICAL_ONLY.includes(k)));
    return M(color, { roughness: 0.35, metalness: 0.05, ...std }, unique);
  };
  const glow = (color, k = 1.6) => M(color, { emissive: color, emissiveIntensity: k, roughness: 0.4 });
  const shade = (o) => {
    o.traverse((c) => {
      if (!c.isMesh) return;
      if (!c.geometry.boundingSphere) c.geometry.computeBoundingSphere();
      c.castShadow = c.geometry.boundingSphere.radius > 0.22; c.receiveShadow = true;
    });
    return o;
  };
  const dyn = (o) => { o.userData.dyn = true; return o; };       // moves or changes shape: never baked
  const box = (w, h, d, m) => shade(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m));
  const rbox = (w, h, d, m, r = 0.05) => shade(new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001)), m));
  const cyl = (rt, rb, h, m, seg = 24, open = false) => shade(new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg, 1, open), m));
  const sphere = (r, m, seg = 20) => shade(new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.7)), m));
  const put = (o, x, y, z, ry = 0) => { o.position.set(x, y, z); o.rotation.y = ry; scene.add(o); return o; };

  // ------------------------------------------------------------------ light
  const hemi = new THREE.HemisphereLight(0xfff6ec, 0xc9b8a6, 0.55);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff0dc, 2.4);
  sun.position.set(14, 34, 26);
  sun.target.position.set(1, 0, 4.5); scene.add(sun.target);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1536, 1536);
  Object.assign(sun.shadow.camera, { left: -34, right: 34, top: 26, bottom: -26, near: 1, far: 110 });
  sun.shadow.bias = -0.0005;
  sun.shadow.normalBias = 0.03;
  sun.shadow.radius = 2;
  scene.add(sun);
  // one warm fill light for the whole floor. Every extra point light is paid for on every pixel of every lit
  // material, so the rooms get their mood from emissive props (lamps, screens, LEDs, neon) instead of six lamps.
  const fill = new THREE.PointLight(0xffd9b0, 16, 46, 1.4); fill.position.set(-2, 8, 4); scene.add(fill);

  // ------------------------------------------------------------------ textures
  function canvasTex(w, h, draw, repeat) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); }
    return t;
  }
  function plankTexture(isDark) {
    return canvasTex(512, 512, (g) => {
      const base = isDark ? [58, 48, 42] : [214, 186, 152];
      for (let row = 0; row < 16; row++) {
        let x = -((row * 97) % 180);
        while (x < 512) {
          const w = 150 + ((row * 31 + Math.abs(x)) % 90);
          const v = ((row * 13 + Math.abs(x) * 7) % 21) - 10;
          g.fillStyle = `rgb(${base[0] + v},${base[1] + v},${base[2] + v * 0.8})`; g.fillRect(x, row * 32, w, 32);
          for (let k = 0; k < 3; k++) { g.fillStyle = `rgba(0,0,0,${isDark ? 0.06 : 0.035})`; g.fillRect(x + 10, row * 32 + 6 + k * 9, w - 20, 1); }
          g.fillStyle = `rgba(0,0,0,${isDark ? 0.35 : 0.13})`; g.fillRect(x, row * 32, 2, 32);
          x += w;
        }
        g.fillStyle = `rgba(0,0,0,${isDark ? 0.4 : 0.15})`; g.fillRect(0, row * 32 + 31, 512, 1.5);
      }
    }, [8.5, 6]);
  }
  function tileTexture(a, b, n = 8, rep = [3, 3]) {
    return canvasTex(256, 256, (g, w) => {
      const s = w / n;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { g.fillStyle = (i + j) % 2 ? a : b; g.fillRect(i * s, j * s, s, s); }
      g.strokeStyle = 'rgba(0,0,0,.12)'; g.lineWidth = 2;
      for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * s, 0); g.lineTo(i * s, w); g.stroke(); g.beginPath(); g.moveTo(0, i * s); g.lineTo(w, i * s); g.stroke(); }
    }, rep);
  }
  function grassTexture(isDark) {
    return canvasTex(256, 256, (g, w, h) => {
      g.fillStyle = isDark ? '#2c4a33' : '#8cc47a'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 2600; i++) {
        const l = isDark ? 18 + Math.random() * 16 : 38 + Math.random() * 22;
        g.fillStyle = `hsl(${100 + Math.random() * 30} ${40 + Math.random() * 20}% ${l}%)`;
        g.fillRect(Math.random() * w, Math.random() * h, 1.5, 3 + Math.random() * 3);
      }
    }, [7, 5]);
  }
  function rubberTexture(isDark) {
    return canvasTex(256, 256, (g, w) => {
      g.fillStyle = isDark ? '#24263a' : '#3d4470'; g.fillRect(0, 0, w, w);
      for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.06})`; g.fillRect(Math.random() * w, Math.random() * w, 2, 2); }
      g.strokeStyle = 'rgba(255,255,255,.08)'; g.lineWidth = 2; g.strokeRect(1, 1, w - 2, w - 2);
    }, [6, 3]);
  }

  // ------------------------------------------------------------------ building (a diorama on a slab)
  const slabMat = M(0xd9cfc2, { roughness: 0.9 }, true);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(150, 64), M(0xe6ded3, { roughness: 1 }, true));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.72; ground.receiveShadow = true; scene.add(ground);
  put(rbox(52.8, 0.7, 33.2, slabMat, 0.3), 1, -0.36, 4.75);
  const floorMat = M(0xffffff, { roughness: 0.62 }, true);
  const pantryFloor = M(0xffffff, { roughness: 0.5 }, true), serverFloor = M(0xffffff, { roughness: 0.45, metalness: 0.15 }, true), carpet = M(0x6d7fa3, { roughness: 0.98 }, true);
  const gameFloor = M(0xffffff, { roughness: 0.85 }, true), grass = M(0xffffff, { roughness: 0.95 }, true);
  const zone = (x0, x1, z0, z1, m, y = 0.008) => { const p = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0), m); p.rotation.x = -Math.PI / 2; p.position.set((x0 + x1) / 2, y, (z0 + z1) / 2); p.receiveShadow = true; scene.add(p); return p; };
  zone(-25, 15, -11.5, 11.5, floorMat);
  zone(-25, -15, 1.5, 11.5, pantryFloor, 0.01); zone(-25, -15, -11.5, -1, serverFloor, 0.01); zone(15, 27, -11.5, 11.5, carpet, 0.01);
  zone(-25, -1, 11.5, 21, gameFloor, 0.01); zone(-1, 27, 11.5, 21, grass, 0.01);

  const wallMat = M(0xf4ede4, { roughness: 0.85 }, true), trimMat = M(0xd8cabb, {}, true), partMat = M(0xe9e0d4, { roughness: 0.85 }, true);
  const glass = M(0xbfe0ff, { emissive: 0x9fd0ff, emissiveIntensity: 0.45, roughness: 0.15 });
  const glassPane = new THREE.MeshStandardMaterial({ color: 0xd5ebff, roughness: 0.06, metalness: 0, transparent: true, opacity: 0.2, depthWrite: false });
  owned.add(glassPane);
  put(box(52.5, 4.6, 0.5, wallMat), 1, 2.3, -11.25);                               // north
  put(box(0.5, 4.6, 32.5, wallMat), -25.25, 2.3, 4.75);                            // west (pantry, game room)
  put(box(0.5, 4.6, 23, wallMat), 27.25, 2.3, 0);                                  // east (meeting room)
  put(box(52.5, 0.28, 0.12, trimMat), 1, 0.14, -10.95);
  for (const x of [5.6, 12]) { put(box(3.4, 2.1, 0.08, glass), x, 2.6, -10.98); put(box(3.6, 0.12, 0.2, trimMat), x, 1.5, -10.95); }
  put(box(0.08, 2.1, 3.4, glass), -24.98, 2.6, 6.8);                              // pantry window
  // interior walls are low (2.4) so the camera sees into every room
  const part = (x, z, w, d) => put(box(w, 2.4, d, partMat), x, 1.2, z);
  part(-15, -5.85, 0.3, 10.3); part(-15, 6.7, 0.3, 9.6);                           // west partition, door at z ≈ 0.6
  part(-23.05, -1, 3.9, 0.3); part(-16.95, -1, 3.9, 0.3);                          // server room wall, door at x ≈ -20
  part(-23.05, 1.5, 3.9, 0.3); part(-16.95, 1.5, 3.9, 0.3);                        // pantry wall, door at x ≈ -20
  function glassWall(x0, z0, x1, z1, h = 2.6) {
    const len = Math.hypot(x1 - x0, z1 - z0), cx = (x0 + x1) / 2, cz = (z0 + z1) / 2, ry = Math.atan2(x1 - x0, z1 - z0);
    const g = new THREE.Mesh(new THREE.BoxGeometry(0.08, h, len), glassPane); g.position.set(cx, h / 2, cz); g.rotation.y = ry; scene.add(g);
    for (const y of [h, 0.06]) { const t = box(0.14, 0.1, len, trimMat); t.position.set(cx, y, cz); t.rotation.y = ry; scene.add(t); }
  }
  glassWall(15, -11, 15, 6.3); glassWall(15, 8.9, 15, 11.5);                        // meeting room, door at z ≈ 7.6
  glassWall(-25, 11.5, -7.2, 11.5); glassWall(-4.8, 11.5, -1, 11.5);                // game room, door at x ≈ -6
  glassWall(-1, 11.5, -1, 15.8); glassWall(-1, 18.2, -1, 21);                       // game room ↔ garden, door at z ≈ 17
  glassWall(15, 11.5, 27, 11.5);                                                    // meeting room ↔ garden
  // garden: hedges to the work floor (gate at x ≈ 6), a low glass balustrade on the open sides
  const hedgeM = M(0x4f8f5a, { roughness: 0.95 }), planterM = M(0xb9a58d, { roughness: 0.8 });
  for (const [x0, x1] of [[-1, 4.9], [7.1, 15]]) {
    const w = x1 - x0, c = (x0 + x1) / 2;
    put(rbox(w, 0.55, 0.7, planterM, 0.08), c, 0.28, 11.5);
    const hd = rbox(w - 0.1, 0.6, 0.6, hedgeM, 0.25); put(hd, c, 0.85, 11.5);
  }
  const balM = new THREE.MeshStandardMaterial({ color: 0xe8f4ff, roughness: 0.05, transparent: true, opacity: 0.25, depthWrite: false }); owned.add(balM);
  for (const [cx, cz, w, d] of [[13, 21, 28, 0.06], [27, 16.25, 0.06, 9.5]]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, 1.1, d), balM); b.position.set(cx, 0.55, cz); scene.add(b);
    put(box(w + 0.05, 0.08, d + 0.1, trimMat), cx, 1.12, cz);
  }
  // room name plates
  function plate(text, x, z, ry = 0, y = 2.15) {
    const t = canvasTex(512, 128, (g, w, h) => { g.fillStyle = '#1f2026'; g.beginPath(); g.roundRect(0, 0, w, h, 26); g.fill(); g.fillStyle = '#fff'; g.font = '600 56px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, w / 2, h / 2 + 2); });
    const m = new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: 0.88 }); owned.add(m);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.38), m); p.position.set(x, y, z); p.rotation.y = ry; scene.add(p);
  }
  plate('Pantry', -18.2, 1.68); plate('Server room', -18.2, -0.83); plate('Meeting room', 15.08, 4.6, Math.PI / 2);
  plate('Game room', -10, 11.58, 0, 2.2); plate('Garden', 4.2, 11.88, 0, 1.45);

  // each room's lamp as a soft pool of coloured light painted on its floor: no light source, so it costs a few pixels
  // instead of a lighting term on every lit pixel of the office (strong at night, faint by day; see setTheme)
  const poolTex = canvasTex(128, 128, (g, w) => { const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, w); });
  const pools = [[-20, 6.5, 6.5, 0xffa95c], [-20, -6.3, 6, 0x4f8cff], [21, -1.5, 9, 0xffe2b8], [-13, 16.2, 9, 0xb46bff], [12.5, 16.2, 10, 0xffc870], [0, 1, 12, 0xffd2a0]]
    .map(([x, z, r, c]) => {
      const m = new THREE.MeshBasicMaterial({ map: poolTex, color: c, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
      owned.add(m);
      const p = new THREE.Mesh(new THREE.PlaneGeometry(r * 2, r * 2), m); p.rotation.x = -Math.PI / 2; p.position.set(x, 0.024, z); p.renderOrder = 1; scene.add(p);
      return m;
    });
  const rug = new THREE.Mesh(new THREE.PlaneGeometry(13, 7.5), M(0xc96f4a, { roughness: 0.95 }));
  rug.rotation.x = -Math.PI / 2; rug.position.set(0, 0.014, 0.6); rug.receiveShadow = true; scene.add(rug);
  const rugIn = new THREE.Mesh(new THREE.PlaneGeometry(11.6, 6.1), M(0xe6c4a0, { roughness: 0.95 }));
  rugIn.rotation.x = -Math.PI / 2; rugIn.position.set(0, 0.018, 0.6); rugIn.receiveShadow = true; scene.add(rugIn);
  const leafMs = [M(0x4f8f5a, { roughness: 0.8 }), M(0x5fa06a, { roughness: 0.8 }), M(0x3f7d4c, { roughness: 0.8 })], potM = P(0xb5684a, { roughness: 0.6, clearcoat: 0.3 });
  const plants = [];
  function plant(x, z, s) {
    const g = new THREE.Group(); g.position.set(x, 0, z); scene.add(g);
    const p = cyl(0.5 * s, 0.36 * s, 0.75 * s, potM, 28); p.position.y = 0.38 * s; g.add(p);
    const rim = cyl(0.53 * s, 0.53 * s, 0.08 * s, potM, 28); rim.position.y = 0.76 * s; g.add(rim);
    for (let i = 0; i < 7; i++) { const b = sphere((0.42 + (i % 3) * 0.08) * s, leafMs[i % 3], 14); b.position.set(Math.cos(i * 1.9) * 0.3 * s, (1.0 + i * 0.2) * s, Math.sin(i * 1.9) * 0.3 * s); b.scale.set(1, 1.2, 1); g.add(b); }
    plants.push(g);
  }
  for (const [x, z, s] of [[-14, -10, 1.2], [14, -10, 1.0], [-14, 10.4, 1.1], [13.8, 10.6, 0.9], [26.2, 10.6, 1.1], [-15.9, -1.9, 0.8], [-24.2, 11, 0.8]]) plant(x, z, s);

  // ------------------------------------------------------------------ station furniture (work floor)
  const wood = M(0xc09469, { roughness: 0.55 }), darkWood = M(0x7d5a3f, { roughness: 0.6 }), metal = M(0x4b4f58, { roughness: 0.35, metalness: 0.6 });
  const paperM = M(0xffffff, { roughness: 0.9 }), chairM = P(0x30343e, { roughness: 0.5 });
  function deskAt(group, w = 2.6, d = 1.1) {
    const top = rbox(w, 0.1, d, wood, 0.04); top.position.y = 1.0; group.add(top);
    for (const sx of [-1, 1]) { const l = rbox(0.08, 0.95, d - 0.15, metal, 0.03); l.position.set(sx * (w / 2 - 0.12), 0.48, 0); group.add(l); }
  }
  function monitorAt(group, hue, x = 0, z = -0.2) {
    const mon = rbox(1.08, 0.68, 0.05, metal, 0.03); mon.position.set(x, 1.58, z); group.add(mon);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.98, 0.58), M(hsl(hue, 0.55, 0.6), { emissive: hsl(hue, 0.7, 0.45), emissiveIntensity: 0.6 }, true));
    scr.position.set(x, 1.58, z - 0.03); scr.rotation.y = Math.PI; group.add(scr);
    const st = cyl(0.04, 0.04, 0.4, metal, 10); st.position.set(x, 1.22, z); group.add(st);
    const ft = rbox(0.34, 0.03, 0.22, metal, 0.01); ft.position.set(x, 1.06, z); group.add(ft);
    return scr;
  }
  function chairAt(group, x, z, ry = 0, m = chairM) {
    // sized for the robots (knees at ~0.45): the seat top is at SEAT_H.chair
    const c = new THREE.Group(); c.position.set(x, 0, z); c.rotation.y = ry;
    const seat = rbox(0.82, 0.12, 0.8, m, 0.06); seat.position.y = SEAT_H.chair - 0.06; c.add(seat);
    const back = rbox(0.8, 0.78, 0.1, m, 0.05); back.position.set(0, SEAT_H.chair + 0.4, -0.36); c.add(back);
    const leg = cyl(0.045, 0.045, SEAT_H.chair - 0.1, metal, 8); leg.position.y = (SEAT_H.chair - 0.1) / 2; c.add(leg);
    for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2; const sp = box(0.36, 0.04, 0.05, metal); sp.position.set(Math.cos(a) * 0.18, 0.04, Math.sin(a) * 0.18); sp.rotation.y = -a; c.add(sp); }
    group.add(c);
    return c;
  }
  const stations = {};
  for (const s of STATIONS) {
    const g = new THREE.Group();
    g.position.set(s.home[0], 0, s.home[1]);
    g.rotation.y = Math.atan2(s.face[0], s.face[1]);
    scene.add(g);
    const parts = { g };
    const pad = new THREE.Mesh(new THREE.CircleGeometry(2.6, 48), new THREE.MeshBasicMaterial({ color: hsl(s.hue, 0.7, 0.6), transparent: true, opacity: 0.12, depthWrite: false }));
    owned.add(pad.material);
    pad.rotation.x = -Math.PI / 2; pad.position.y = 0.022; g.add(pad); parts.pad = pad;
    // desks sit 0.2 lower than they are modelled (top at ~0.85, elbow height for a seated robot); the legs just go
    // through the floor, where nobody sees them
    const deskG = new THREE.Group(); deskG.position.set(0, -0.2, 1.35); g.add(deskG); parts.desk = deskG;
    chairAt(g, 0, -0.25);
    if (s.prop === 'desk') { deskAt(deskG); parts.screen = monitorAt(deskG, s.hue); }
    if (s.prop === 'board') {
      deskAt(deskG, 2.2, 0.9);
      const bd = rbox(3.2, 2.0, 0.08, M(0xfcfcfa), 0.03); bd.position.set(0, 2.3, -1.9); g.add(bd);
      const fr = rbox(3.4, 0.1, 0.25, trimMat, 0.03); fr.position.set(0, 1.26, -1.86); g.add(fr);
      for (const x of [-1.5, 1.5]) { const l = cyl(0.04, 0.04, 1.3, metal, 8); l.position.set(x, 0.65, -1.9); g.add(l); }
      parts.lines = [];
      for (let i = 0; i < 5; i++) {
        const w = 0.6 + ((i * 7) % 5) * 0.32;
        const l = box(w, 0.08, 0.02, M(hsl(s.hue + i * 35, 0.6, 0.5))); l.position.set(-1.0 + w / 2, 2.95 - i * 0.3, -1.85); g.add(dyn(l)); parts.lines.push(l);
      }
    }
    if (s.prop === 'portal') {
      deskAt(deskG, 2.0, 0.9);
      const globe = dyn(sphere(0.36, P(hsl(s.hue, 0.6, 0.6), { emissive: hsl(s.hue, 0.7, 0.35), emissiveIntensity: 0.4 }), 24)); globe.position.set(0.5, 1.45, 0); deskG.add(globe); parts.globe = globe;
      const arch = new THREE.Group(); arch.position.set(0, 0, -3.15); g.add(arch);
      const ringM = M(hsl(s.hue, 0.8, 0.55), { emissive: hsl(s.hue, 0.9, 0.5), emissiveIntensity: 1.1 }, true);
      const ring = shade(new THREE.Mesh(new THREE.TorusGeometry(1.3, 0.14, 14, 48, Math.PI), ringM)); ring.position.y = 1.9; arch.add(ring);
      for (const x of [-1.3, 1.3]) { const p = cyl(0.14, 0.14, 1.9, ringM, 12); p.position.set(x, 0.95, 0); arch.add(p); }
      const veil = new THREE.Mesh(new THREE.PlaneGeometry(2.45, 3.1), new THREE.MeshBasicMaterial({ color: hsl(s.hue, 0.95, 0.75), transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
      owned.add(veil.material); veil.position.set(0, 1.55, 0.02); arch.add(veil);
      parts.portal = { arch, veil, ringM };
    }
    if (s.prop === 'shelf') {
      deskAt(deskG, 2.2, 0.9);
      const sh = rbox(3.0, 3.2, 0.7, darkWood, 0.04); sh.position.set(0, 1.6, -2.4); g.add(sh);
      for (let r = 0; r < 4; r++) for (let i = 0; i < 8; i++) {
        const bk = box(0.26, 0.5 + ((i * 7 + r) % 3) * 0.1, 0.5, M(hsl(s.hue + i * 41 + r * 70, 0.45, 0.55)));
        bk.position.set(-1.15 + i * 0.33, 0.45 + r * 0.76, -2.05); g.add(bk);
      }
    }
    if (s.prop === 'sorter') {
      deskAt(deskG, 3.0, 1.2);
      for (let i = 0; i < 3; i++) { const t = rbox(0.75, 0.08, 0.9, M(hsl(s.hue + i * 25, 0.5, 0.6)), 0.03); t.position.set(0.3 + i * 0.85 - 0.85, 1.1, 0); deskG.add(t); }
    }
    if (s.prop === 'stamp') {
      deskAt(deskG, 2.4, 1.0);
      const stamp = dyn(new THREE.Group()); stamp.position.set(0.55, 1.06, 0.0); deskG.add(stamp);
      const sb = cyl(0.22, 0.26, 0.14, P(hsl(s.hue, 0.6, 0.42))); sb.position.y = 0.07; stamp.add(sb);
      const sh = cyl(0.07, 0.09, 0.42, wood, 10); sh.position.y = 0.35; stamp.add(sh);
      const kn = sphere(0.13, wood, 12); kn.position.y = 0.6; stamp.add(kn);
      parts.stamp = stamp;
    }
    if (s.prop === 'chart') {
      deskAt(deskG); parts.screen = monitorAt(deskG, s.hue, -0.4);
      parts.bars = [];
      for (let i = 0; i < 4; i++) {
        const b = box(0.2, 1, 0.2, M(hsl(s.hue + i * 15, 0.65, 0.55), { emissive: hsl(s.hue, 0.6, 0.3), emissiveIntensity: 0.25 }));
        b.position.set(0.55 + (i % 2) * 0.28, 1.2, -0.15 + Math.floor(i / 2) * 0.28); b.scale.y = 0.15; deskG.add(dyn(b)); parts.bars.push(b);
      }
    }
    if (s.prop === 'podium') {
      for (const [x, h, c] of [[0, 1.0, 0.82], [-0.95, 0.68, 0.72], [0.95, 0.45, 0.66]]) { const st = rbox(0.92, h, 0.92, P(hsl(s.hue, 0.4, c)), 0.05); st.position.set(x, h / 2, 1.5); g.add(st); }
      const gold = P(0xe7b54a, { metalness: 0.85, roughness: 0.22, emissive: 0x6b4a10, emissiveIntensity: 0.25 });
      const trophy = dyn(new THREE.Group()); trophy.position.set(0, 1.0, 1.5); g.add(trophy);
      const tb = cyl(0.22, 0.28, 0.14, gold); tb.position.y = 0.07; trophy.add(tb);
      const stem = cyl(0.06, 0.08, 0.35, gold, 10); stem.position.y = 0.3; trophy.add(stem);
      const cup = cyl(0.34, 0.14, 0.5, gold); cup.position.y = 0.72; trophy.add(cup);
      parts.trophy = trophy;
      parts.board = new THREE.Group(); parts.board.position.set(-2.2, 0, 0.4); parts.board.rotation.y = 0.55; g.add(parts.board);
      const bb2 = rbox(1.6, 2.2, 0.08, M(0x2f3440), 0.03); bb2.position.y = 2.0; parts.board.add(bb2);
      const bl = box(0.1, 1.0, 0.1, metal); bl.position.y = 0.5; parts.board.add(bl);
      parts.cards = dyn(new THREE.Group()); parts.board.add(parts.cards);
    }
    if (s.prop === 'network') {
      // the Connector: a laptop, a tray of letters and a cork board of people joined by red string
      deskAt(deskG, 2.6, 1.05);
      const lap = new THREE.Group(); lap.position.set(-0.2, 1.05, 0.05); deskG.add(lap);
      const base = rbox(0.86, 0.04, 0.58, metal, 0.015); base.position.y = 0.02; lap.add(base);
      const lid = new THREE.Group(); lid.position.set(0, 0.04, -0.28); lid.rotation.x = -0.32; lap.add(lid);
      const lb = rbox(0.86, 0.56, 0.03, metal, 0.015); lb.position.y = 0.28; lid.add(lb);
      parts.screen = new THREE.Mesh(new THREE.PlaneGeometry(0.78, 0.48), M(hsl(s.hue, 0.5, 0.6), { emissive: hsl(s.hue, 0.7, 0.45), emissiveIntensity: 0.6 }, true));
      parts.screen.position.set(0, 0.28, 0.017); lid.add(parts.screen);
      const tray = rbox(0.6, 0.08, 0.42, darkWood, 0.02); tray.position.set(0.85, 1.09, 0.05); deskG.add(tray);
      const envM = M(0xfff4dc, { roughness: 0.9 });
      for (let i = 0; i < 4; i++) { const e = box(0.5, 0.02, 0.32, envM); e.position.set(0.85, 1.15 + i * 0.025, 0.05); e.rotation.y = (i - 1.5) * 0.08; deskG.add(e); }
      const cork = rbox(2.8, 1.7, 0.08, M(0xc8a27a, { roughness: 1 }), 0.03); cork.position.set(0, 2.25, -1.9); g.add(cork);
      const frame = rbox(2.92, 1.82, 0.05, darkWood, 0.03); frame.position.set(0, 2.25, -1.95); g.add(frame);
      for (const x of [-1.3, 1.3]) { const l = cyl(0.04, 0.04, 1.4, metal, 8); l.position.set(x, 0.7, -1.9); g.add(l); }
      const pts = [[-1.0, 2.75], [-0.1, 2.85], [0.9, 2.7], [-0.75, 1.85], [0.3, 1.95], [1.05, 1.8]];
      parts.people = [];
      pts.forEach(([x, y], i) => {
        const t = canvasTex(96, 120, (gg, w, h) => { gg.fillStyle = '#fff'; gg.fillRect(0, 0, w, h); gg.fillStyle = `hsl(${(i * 67) % 360} 55% 62%)`; gg.fillRect(6, 6, w - 12, h - 30); gg.fillStyle = '#fff'; gg.beginPath(); gg.arc(w / 2, 42, 17, 0, Math.PI * 2); gg.fill(); gg.beginPath(); gg.ellipse(w / 2, 86, 28, 18, 0, Math.PI, 0); gg.fill(); gg.fillStyle = '#555'; gg.fillRect(16, h - 18, w - 32, 5); });
        const m = new THREE.MeshStandardMaterial({ map: t, roughness: 0.9 }); owned.add(m);
        const c = new THREE.Mesh(new THREE.PlaneGeometry(0.38, 0.48), m); c.position.set(x, y, -1.85); c.rotation.z = (i % 2 ? 1 : -1) * 0.06; g.add(dyn(c)); parts.people.push(c);
        const pin = sphere(0.035, glow(0xe0483d, 0.4), 8); pin.position.set(x, y + 0.22, -1.83); g.add(pin);
      });
      const stringM = M(0xd2483d, { emissive: 0x8a1a12, emissiveIntensity: 0.5 });
      for (const [a, b] of [[0, 1], [1, 2], [0, 3], [1, 4], [2, 5], [3, 4], [4, 5], [1, 5]]) {
        const p0 = new THREE.Vector3(pts[a][0], pts[a][1] + 0.22, -1.82), p1 = new THREE.Vector3(pts[b][0], pts[b][1] + 0.22, -1.82);
        const len = p0.distanceTo(p1), st = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, len, 5), stringM);
        st.position.copy(p0).add(p1).multiplyScalar(0.5); st.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p1.clone().sub(p0).normalize()); g.add(st);
      }
    }
    const pile = dyn(new THREE.Group()); pile.position.set(-0.75, 1.07, 0.1); deskG.add(pile); parts.pile = pile; parts.count = 0;
    if (s.key === 'validate' || s.key === 'match') {
      // on the left of the desk: the walk out to the front of the desk passes on the right (sideOut → sideFront)
      const bin = cyl(0.42, 0.34, 0.8, P(0x6b717c), 24, true); bin.position.set(-1.9, 0.4, 1.1); g.add(bin);
      parts.bin = dyn(new THREE.Group()); parts.bin.position.set(-1.9, 0, 1.1); g.add(parts.bin); parts.binCount = 0;
    }
    stations[s.key] = parts;
  }

  // ------------------------------------------------------------------ pantry
  const white = P(0xf7f5f0, { roughness: 0.3 }), red = M(0xd2483d, { emissive: 0x7a1a12, emissiveIntensity: 0.4 }), teal = P(0x3c8f8a);
  put(rbox(1.0, 1.0, 6.4, darkWood, 0.04), -24.25, 0.5, 6.4);
  put(rbox(1.1, 0.08, 6.5, P(0xe8e2d8, { roughness: 0.25 }), 0.02), -24.25, 1.04, 6.4);
  const coffee = new THREE.Group(); put(coffee, -24.3, 1.08, 4.4);
  { const b = rbox(0.6, 0.8, 0.55, P(0x2a2c31, { metalness: 0.5, roughness: 0.3 }), 0.06); b.position.y = 0.4; coffee.add(b);
    const l = box(0.08, 0.08, 0.02, red); l.position.set(0.31, 0.62, 0); l.rotation.y = Math.PI / 2; coffee.add(l);
    const cup = cyl(0.09, 0.07, 0.14, white, 12); cup.position.set(0.18, 0.08, 0); coffee.add(cup); }
  const kettle = cyl(0.22, 0.26, 0.4, P(0xc0c4cc, { metalness: 0.85, roughness: 0.2 })); put(kettle, -24.3, 1.28, 5.5);
  put(rbox(1.0, 2.3, 1.0, white, 0.08), -24.2, 1.15, 2.4);                           // fridge
  put(box(0.03, 0.9, 0.06, metal), -23.68, 1.5, 2.15);
  const cooler = new THREE.Group(); put(cooler, -15.8, 0, 10.6);
  { const b = rbox(0.6, 1.1, 0.6, white, 0.06); b.position.y = 0.55; cooler.add(b);
    const bottle = cyl(0.25, 0.25, 0.7, P(0x8fc8ff, { transparent: true, opacity: 0.7, roughness: 0.05 }), 16); bottle.position.y = 1.45; cooler.add(bottle); }
  const tableTop = cyl(0.95, 0.95, 0.08, wood, 40); put(tableTop, -20, 0.8, 7.2);
  put(cyl(0.08, 0.1, 0.8, metal, 10), -20, 0.4, 7.2);
  for (const x of [-21.25, -18.75]) { put(cyl(0.32, 0.32, 0.08, teal, 16), x, STOOL_H - 0.04, 7.2); put(cyl(0.05, 0.05, STOOL_H - 0.08, metal, 8), x, (STOOL_H - 0.08) / 2, 7.2); }
  const sofa = new THREE.Group(); put(sofa, -21, 0, 10.8, Math.PI);
  { const sm = P(0x9a5d7a, { roughness: 0.9, clearcoat: 0, sheen: 1, sheenColor: new THREE.Color(0xd9a0bf) });
    const seat = rbox(3.0, 0.5, 1.0, sm, 0.15); seat.position.y = SEAT_H.sofa - 0.25; sofa.add(seat);
    const back = rbox(3.0, 0.9, 0.3, sm, 0.12); back.position.set(0, SEAT_H.sofa + 0.25, -0.42); sofa.add(back);
    for (const x of [-1.6, 1.6]) { const a = rbox(0.3, 0.6, 1.0, sm, 0.12); a.position.set(x, SEAT_H.sofa - 0.05, 0); sofa.add(a); } }
  // wall clock (real time) on the pantry wall
  const clockTex = canvasTex(256, 256, () => {});
  const clockMat = new THREE.MeshBasicMaterial({ map: clockTex, transparent: true }); owned.add(clockMat);
  const clockFace = new THREE.Mesh(new THREE.CircleGeometry(0.5, 40), clockMat); clockFace.position.set(-22.6, 1.85, 1.67); scene.add(clockFace);
  let clockMinute = -1;
  function drawClock() {
    const d = new Date(); const m = d.getHours() * 60 + d.getMinutes();
    if (m === clockMinute) return; clockMinute = m;
    const c = clockTex.image, g = c.getContext('2d'), r = 120;
    g.clearRect(0, 0, 256, 256);
    g.fillStyle = '#fbfaf7'; g.beginPath(); g.arc(128, 128, r, 0, Math.PI * 2); g.fill();
    g.lineWidth = 10; g.strokeStyle = '#2b2d33'; g.stroke();
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; g.lineWidth = i % 3 ? 3 : 7; g.beginPath(); g.moveTo(128 + Math.sin(a) * 96, 128 - Math.cos(a) * 96); g.lineTo(128 + Math.sin(a) * 108, 128 - Math.cos(a) * 108); g.stroke(); }
    const hand = (a, len, w, col) => { g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.beginPath(); g.moveTo(128, 128); g.lineTo(128 + Math.sin(a) * len, 128 - Math.cos(a) * len); g.stroke(); };
    hand(((d.getHours() % 12) + d.getMinutes() / 60) / 12 * Math.PI * 2, 58, 9, '#2b2d33');
    hand(d.getMinutes() / 60 * Math.PI * 2, 86, 6, '#2b2d33');
    g.fillStyle = '#d2483d'; g.beginPath(); g.arc(128, 128, 8, 0, Math.PI * 2); g.fill();
    clockTex.needsUpdate = true;
  }
  const steamM = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.0, depthWrite: false }); owned.add(steamM);
  const steam = []; for (let i = 0; i < 6; i++) { const p = dyn(new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), steamM.clone())); owned.add(p.material); p.visible = false; scene.add(p); steam.push({ p, t: i / 6 }); }
  let brewing = 0;

  // ------------------------------------------------------------------ server room
  const rackM = P(0x23262d, { metalness: 0.4, roughness: 0.4 });
  const ledMats = [0x44e08a, 0x5aa8ff, 0xffb547].map((c) => M(c, { emissive: c, emissiveIntensity: 1.2 }, true));
  function rack(x, z, ry) {
    const g = new THREE.Group(); put(g, x, 0, z, ry);
    const b = rbox(1.2, 2.8, 0.9, rackM, 0.04); b.position.y = 1.4; g.add(b);
    for (let i = 0; i < 9; i++) {
      const u = box(1.0, 0.04, 0.02, M(0x3a3e47)); u.position.set(0, 0.4 + i * 0.27, 0.46); g.add(u);
      for (let j = 0; j < 3; j++) { const l = new THREE.Mesh(new THREE.PlaneGeometry(0.07, 0.05), ledMats[(i + j) % 3]); l.position.set(-0.38 + j * 0.12, 0.5 + i * 0.27, 0.461); g.add(l); }
    }
  }
  for (let i = 0; i < 5; i++) rack(-23.6 + i * 1.6, -10.35, 0);
  for (let i = 0; i < 3; i++) rack(-24.45, -7.6 + i * 1.6, Math.PI / 2);
  { const g = new THREE.Group(); put(g, -16.9, 0, -5.2, -Math.PI / 2); deskAt(g, 1.8, 0.8); monitorAt(g, 205, 0, -0.1); }

  // ------------------------------------------------------------------ meeting room
  put(rbox(1.7, 0.12, 9.2, wood, 0.05), 21, 0.8, -2.6);
  for (const z of [-6.6, 1.4]) put(rbox(0.3, 0.78, 0.3, metal, 0.04), 21, 0.39, z);
  const meetChairs = [];
  for (const z of [-6, -4, -2, 0]) for (const [x, ry] of [[19.55, Math.PI / 2], [22.45, -Math.PI / 2]]) {
    const g = new THREE.Group(); scene.add(g);
    chairAt(g, x, z, ry);
    meetChairs.push({ pos: V(x, z), face: ry, busy: false, h: SEAT_H.chair });
  }
  const boardTex = canvasTex(1024, 512, () => {});
  const tickerTex = canvasTex(1024, 320, () => {});
  for (const [tex, w, h, x, y, z] of [[boardTex, 5.4, 2.7, 21, 2.6, -10.94], [tickerTex, 3.4, 1.06, 0.2, 3.72, -10.96]]) {
    const m = new THREE.MeshBasicMaterial({ map: tex }); owned.add(m);
    const s = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m); s.position.set(x, y, z); scene.add(s);
    put(rbox(w + 0.2, h + 0.2, 0.06, M(0x1b1c21), 0.04), x, y, z - 0.04);
  }
  const loungeBags = [[24.4, 8.2, 0xe2a04a], [25.6, 9.6, 0x4a90c2], [23.4, 9.9, 0x8bbf6a]];
  for (const [x, z, c] of loungeBags) { const b = sphere(0.65, P(c, { roughness: 0.85, clearcoat: 0, sheen: 1 }), 20); b.scale.set(1, 0.6, 1); put(b, x, 0.4, z); }
  put(rbox(0.06, 1.6, 2.8, M(0xfcfcfa), 0.02), 27.0, 2.0, 3.2);                     // whiteboard

  // ------------------------------------------------------------------ game room
  const neon = (txt, color) => canvasTex(512, 160, (g, w, h) => { g.clearRect(0, 0, w, h); g.font = '800 104px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.shadowColor = color; g.shadowBlur = 24; g.fillStyle = color; g.fillText(txt, w / 2, h / 2); g.fillStyle = '#fff'; g.shadowBlur = 0; g.globalAlpha = 0.85; g.fillText(txt, w / 2, h / 2); });
  { const m = new THREE.MeshBasicMaterial({ map: neon('PLAY', '#d77dff'), transparent: true, toneMapped: false }); owned.add(m);
    const s = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.0), m); s.position.set(-24.95, 2.9, 17.6); s.rotation.y = Math.PI / 2; scene.add(s); }
  const ttBlue = P(0x1f5fa8, { roughness: 0.4 }), lineW = M(0xffffff, { roughness: 0.5 });
  const TT = { x: -14, z: 16, len: 4.2, wid: 2.3, h: 0.95 };
  put(rbox(TT.len, 0.08, TT.wid, ttBlue, 0.03), TT.x, TT.h - 0.04, TT.z);
  put(box(TT.len, 0.005, 0.03, lineW), TT.x, TT.h + 0.003, TT.z);
  for (const [lx, lz] of [[-1.7, -0.95], [1.7, -0.95], [-1.7, 0.95], [1.7, 0.95]]) put(cyl(0.05, 0.05, TT.h - 0.08, metal, 8), TT.x + lx, (TT.h - 0.08) / 2, TT.z + lz);
  { const net = new THREE.Mesh(new THREE.PlaneGeometry(TT.wid + 0.2, 0.18), new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.75, side: THREE.DoubleSide })); owned.add(net.material);
    net.position.set(TT.x, TT.h + 0.09, TT.z); net.rotation.y = Math.PI / 2; scene.add(net); }
  const ball = dyn(sphere(0.07, glow(0xfff4e0, 0.5), 12)); ball.visible = false; scene.add(ball);
  // foosball
  const FB = { x: -5, z: 19.4 };
  put(rbox(2.4, 0.5, 1.25, P(0x2d6a3e), 0.06), FB.x, 0.95, FB.z);
  put(rbox(2.2, 0.02, 1.05, M(0x3c9a54), 0.01), FB.x, 1.21, FB.z);
  for (const [lx, lz] of [[-1.05, -0.5], [1.05, -0.5], [-1.05, 0.5], [1.05, 0.5]]) put(rbox(0.12, 0.72, 0.12, darkWood, 0.03), FB.x + lx, 0.36, FB.z + lz);
  const rods = [];
  for (let i = 0; i < 4; i++) {
    const r = dyn(new THREE.Group()); put(r, FB.x - 0.75 + i * 0.5, 1.32, FB.z);
    const bar = cyl(0.02, 0.02, 1.7, metal, 6); bar.rotation.x = Math.PI / 2; r.add(bar);
    for (const z of [-0.3, 0, 0.3]) { const man = rbox(0.07, 0.22, 0.09, M(i % 2 ? 0xe3473b : 0x3b7ee3), 0.02); man.position.set(0, -0.08, z); r.add(man); }
    rods.push(r);
  }
  const fball = dyn(sphere(0.045, white, 10)); fball.position.set(FB.x, 1.26, FB.z); scene.add(fball);
  // arcade cabinets with live screens
  const arcades = [];
  for (const [z, hue] of [[13.8, 290], [15.6, 190]]) {
    const g = new THREE.Group(); put(g, -24.4, 0, z, Math.PI / 2);
    const body = rbox(1.1, 2.3, 0.95, P(hsl(hue, 0.55, 0.32)), 0.06); body.position.y = 1.15; g.add(body);
    const panel = rbox(1.1, 0.12, 0.5, P(0x1a1b22), 0.03); panel.position.set(0, 1.12, 0.6); panel.rotation.x = -0.3; g.add(panel);
    for (const [x, c] of [[-0.25, 0xff4d4d], [0.05, 0x4dd2ff], [0.25, 0xffd84d]]) { const b = cyl(0.05, 0.05, 0.05, glow(c, 0.8), 10); b.position.set(x, 1.2, 0.65); g.add(b); }
    const tex = canvasTex(128, 112, (gg, w, h) => { gg.fillStyle = '#05060a'; gg.fillRect(0, 0, w, h); });
    const sm = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }); owned.add(sm);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.82, 0.7), sm); scr.position.set(0, 1.75, 0.485); g.add(scr);
    const mq = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.25), glow(hsl(hue, 0.9, 0.6), 1.2)); mq.position.set(0, 2.18, 0.48); g.add(mq);
    arcades.push({ g, tex, busy: false, play: 0, t: 0, score: 0, spot: { pos: V(-23.15, z), face: -Math.PI / 2 } });
  }
  function drawArcade(a, dt) {
    a.t += dt; a.acc = (a.acc || 0) + dt;
    if (a.acc < 1 / 15) return;
    a.acc = 0;
    const g = a.tex.image.getContext('2d'), w = 128, h = 112;
    g.fillStyle = '#05060a'; g.fillRect(0, 0, w, h);
    if (!a.play) { g.fillStyle = `rgba(120,200,255,${0.4 + 0.3 * Math.sin(a.t * 3)})`; g.font = '700 14px monospace'; g.textAlign = 'center'; g.fillText('INSERT', w / 2, h / 2 - 6); g.fillText('COIN', w / 2, h / 2 + 12); a.tex.needsUpdate = true; return; }
    for (let i = 0; i < 18; i++) { g.fillStyle = `hsl(${(i * 40 + a.t * 120) % 360} 90% 60%)`; g.fillRect((i * 37 + a.t * 60) % w, (i * 23 + a.t * (30 + i * 4)) % h, 6, 6); }
    g.fillStyle = '#fff'; g.fillRect(w / 2 - 8 + Math.sin(a.t * 9) * 30, h - 16, 16, 8);
    g.font = '700 11px monospace'; g.textAlign = 'left'; g.fillText(`${Math.floor(a.score)}`, 6, 13);
    a.tex.needsUpdate = true;
  }
  const bagSpots = [];
  for (const [x, z, c] of [[-21.6, 19.7, 0xf06292], [-19.7, 20.0, 0xffb74d]]) { const b = sphere(0.72, P(c, { roughness: 0.85 }), 22); b.scale.set(1, 0.5, 1); put(b, x, 0.2, z); bagSpots.push({ pos: V(x, z), seat: true, face: 0, h: 0.42 }); }
  { const r = new THREE.Mesh(new THREE.CircleGeometry(2.4, 40), M(0x6a4fb3, { roughness: 1 })); r.rotation.x = -Math.PI / 2; r.position.set(-20.5, 0.02, 19.6); r.receiveShadow = true; scene.add(r); }

  // ------------------------------------------------------------------ garden
  const stoneM = M(0xd8d2c8, { roughness: 0.9 });
  for (const [x, z] of [[6, 12.3], [6.1, 13.3], [6.4, 14.3], [7.3, 15.0], [8.4, 14.7], [10.8, 14.6], [12, 15.2]]) { const s = cyl(0.42, 0.42, 0.05, stoneM, 14); s.scale.set(1, 1, 0.8); put(s, x, 0.03, z); }
  const FOUNT = { x: 9, z: 16.5, r: 1.4 };
  put(cyl(FOUNT.r + 0.15, FOUNT.r + 0.25, 0.5, P(0xcfc6b8, { roughness: 0.6 }), 40), FOUNT.x, 0.25, FOUNT.z);
  const water = new THREE.Mesh(new THREE.CircleGeometry(FOUNT.r, 40), P(0x6fb7e0, { roughness: 0.05, metalness: 0.1, transmission: 0, transparent: true, opacity: 0.85, emissive: 0x2a6f99, emissiveIntensity: 0.25 }, true));
  water.rotation.x = -Math.PI / 2; water.position.set(FOUNT.x, 0.46, FOUNT.z); scene.add(water);
  put(cyl(0.15, 0.22, 1.1, P(0xcfc6b8), 16), FOUNT.x, 0.75, FOUNT.z);
  put(cyl(0.6, 0.3, 0.16, P(0xcfc6b8), 24), FOUNT.x, 1.35, FOUNT.z);
  const jet = []; for (let i = 0; i < 10; i++) { const d = sphere(0.05, M(0xbfe6ff, { transparent: true, opacity: 0.8, emissive: 0x6fb7e0, emissiveIntensity: 0.4 }), 6); scene.add(dyn(d)); jet.push({ d, t: i / 10, a: i / 10 * Math.PI * 2 }); }
  const ripples = []; for (let i = 0; i < 2; i++) { const r = new THREE.Mesh(new THREE.RingGeometry(0.2, 0.26, 32), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 })); owned.add(r.material); r.rotation.x = -Math.PI / 2; r.position.set(FOUNT.x, 0.47, FOUNT.z); scene.add(dyn(r)); ripples.push({ r, t: 1 }); }
  const trunkM = M(0x7b5a3f, { roughness: 0.9 });
  function tree(x, z, s = 1, hue = 120) {
    const g = new THREE.Group(); put(g, x, 0, z);
    const t = cyl(0.14 * s, 0.22 * s, 2.2 * s, trunkM, 10); t.position.y = 1.1 * s; g.add(t);
    for (let i = 0; i < 6; i++) { const b = sphere((0.7 + (i % 3) * 0.18) * s, M(hsl(hue + i * 6, 0.42, 0.38 + (i % 3) * 0.06), { roughness: 0.85 }), 14); b.position.set(Math.cos(i * 2.1) * 0.55 * s, (2.5 + (i % 3) * 0.35) * s, Math.sin(i * 2.1) * 0.55 * s); g.add(b); }
    plants.push(g);
  }
  tree(1.6, 20.1, 1.05); tree(16.6, 20.4, 0.95, 105); tree(25.6, 19.8, 1.1, 130); tree(25.4, 12.9, 0.9, 95);
  for (const [x, z, c] of [[3.2, 12.4, 0xf06292], [10.5, 12.4, 0xffd54f], [19.5, 20.3, 0xba68c8], [23.5, 12.5, 0xff8a65]]) {
    put(rbox(1.8, 0.35, 0.8, planterM, 0.06), x, 0.18, z);
    for (let i = 0; i < 7; i++) { const f = sphere(0.1, M(c, { emissive: c, emissiveIntensity: 0.15 }), 8); put(f, x - 0.7 + i * 0.23, 0.45 + (i % 2) * 0.08, z + (i % 3 - 1) * 0.15); }
  }
  const benchM = M(0xa77b52, { roughness: 0.6 });
  { const g = new THREE.Group(); put(g, 14, 0, 19.75, 0);
    const s = rbox(2.6, 0.1, 0.6, benchM, 0.03); s.position.y = BENCH_H - 0.05; g.add(s);
    const b = rbox(2.6, 0.5, 0.08, benchM, 0.03); b.position.set(0, BENCH_H + 0.32, -0.3); b.rotation.x = -0.12; g.add(b);
    for (const x of [-1.1, 1.1]) { const l = rbox(0.1, BENCH_H - 0.07, 0.5, metal, 0.02); l.position.set(x, (BENCH_H - 0.07) / 2, 0); g.add(l); } }
  const benchSpots = [{ pos: V(13.4, 19.65), seat: true, face: 0, h: BENCH_H }, { pos: V(14.6, 19.65), seat: true, face: 0, h: BENCH_H }];
  // swing: an A-frame; the seat swings and whoever sits on it swings with it
  const SW = { x: 21.5, z: 16, top: 3.1 };
  for (const x of [SW.x - 1.3, SW.x + 1.3]) for (const dz of [-0.8, 0.8]) { const l = cyl(0.07, 0.07, 3.3, P(0xe8e2d8), 8); l.position.set(x, 1.55, SW.z + dz / 2); l.rotation.x = dz > 0 ? -0.26 : 0.26; scene.add(l); shade(l); }
  put(cyl(0.08, 0.08, 2.8, P(0xe8e2d8), 10), SW.x, SW.top, SW.z).rotation.z = Math.PI / 2;
  const swing = dyn(new THREE.Group()); swing.position.set(SW.x, SW.top, SW.z); scene.add(swing);
  for (const x of [-0.42, 0.42]) { const r = cyl(0.015, 0.015, SW.top - 0.44, metal, 5); r.position.set(x, -(SW.top - 0.44) / 2, 0); swing.add(r); }
  const seat = rbox(1.0, 0.07, 0.42, benchM, 0.03); seat.position.set(0, 0.44 - SW.top, 0); swing.add(seat);
  const swingSpot = { pos: V(SW.x, SW.z), seat: true, face: 0, busy: false };
  let swingAmp = 0, swingT = 0;
  // fairy lights on poles across the garden (they glow at night)
  const bulbM = M(0xffe2a8, { emissive: 0xffd27a, emissiveIntensity: 1.4 }, true);
  const wireM = new THREE.LineBasicMaterial({ color: 0x3a3a3a }); owned.add(wireM);
  const poles = [[-0.4, 12.2], [15, 12.4], [26.5, 12.2], [-0.4, 20.6], [15, 20.7], [26.5, 20.6]];
  for (const [x, z] of poles) { const p = cyl(0.06, 0.08, 3.4, metal, 8); put(p, x, 1.7, z); }
  for (const [a, b] of [[0, 1], [1, 2], [3, 4], [4, 5], [0, 4], [1, 5]]) {
    const p0 = V(poles[a][0], poles[a][1], 3.35), p1 = V(poles[b][0], poles[b][1], 3.35), n = Math.round(p0.distanceTo(p1) / 0.9);
    const wire = [];
    for (let i = 0; i <= n; i++) { const u = i / n; const q = p0.clone().lerp(p1, u); q.y -= Math.sin(Math.PI * u) * 0.7; wire.push(q); if (i > 0 && i < n) { const bb = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 5), bulbM); bb.position.copy(q); scene.add(bb); } }
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(wire), wireM));
  }

  // ------------------------------------------------------------------ papers, planes, cards, confetti, notes
  const paperGeo = new THREE.BoxGeometry(0.5, 0.025, 0.66);
  const tweens = [];
  const flying = [];
  function setPile(key, n) {
    const st = stations[key]; st.count = Math.max(0, n);
    const want = Math.min(10, st.count);
    while (st.pile.children.length < want) {
      const p = new THREE.Mesh(paperGeo, paperM);
      p.position.y = st.pile.children.length * 0.03; p.rotation.y = (Math.random() - 0.5) * 0.3; st.pile.add(p);
    }
    while (st.pile.children.length > want) st.pile.remove(st.pile.children[st.pile.children.length - 1]);
  }
  function addToBin(key) {
    const st = stations[key]; if (!st.bin) return;
    st.binCount++;
    if (st.bin.children.length < 6) {
      const p = new THREE.Mesh(paperGeo, paperM); p.scale.setScalar(0.7);
      p.position.set((Math.random() - 0.5) * 0.3, 0.15 + st.bin.children.length * 0.08, (Math.random() - 0.5) * 0.3);
      p.rotation.set(Math.random(), Math.random() * 3, Math.random()); st.bin.add(p);
    }
  }
  const cardM = M(0x67c08a, { emissive: 0x2f8a55, emissiveIntensity: 0.35 });
  function addResultCard() {
    const cards = stations.rank.cards; const i = cards.children.length; if (i >= 8) return;
    const c = rbox(0.62, 0.36, 0.03, cardM, 0.01);
    c.position.set(-0.36 + (i % 2) * 0.72, 2.85 - Math.floor(i / 2) * 0.48, 0.07); c.scale.set(0.01, 0.01, 1); cards.add(c);
    tweens.push({ t: 0, d: 0.5, fn: (k) => c.scale.set(k, k, 1) });
  }
  const planeGeo = new THREE.BufferGeometry();
  planeGeo.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0.32, -0.2, 0, -0.16, 0, 0.04, -0.12, 0, 0, 0.32, 0, 0.04, -0.12, 0.2, 0, -0.16], 3));
  planeGeo.computeVertexNormals();
  const planeM = new THREE.MeshStandardMaterial({ color: 0xffffff, side: THREE.DoubleSide, roughness: 0.8 }); owned.add(planeM);
  /** A paper plane from the Connector's desk out over the garden: a note on its way to a real person. */
  function launchPlane(from) {
    const p = new THREE.Mesh(planeGeo, planeM); p.position.copy(from); scene.add(p);
    const to = V(rand(-2, 14), rand(24, 30), rand(4, 7));
    flying.push({ p, from: from.clone(), to, t: 0, d: 2.6, plane: true });
  }
  const confetti = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.12, 0.08), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }), 220);
  owned.add(confetti.material); confetti.visible = false; scene.add(dyn(confetti));
  const conf = Array.from({ length: 220 }, () => ({ p: new THREE.Vector3(), v: new THREE.Vector3(), r: new THREE.Euler(), s: rand(2, 6) }));
  { const c = new THREE.Color(); for (let i = 0; i < 220; i++) confetti.setColorAt(i, c.setHSL(Math.random(), 0.85, 0.6)); }
  let partyUntil = 0;
  function throwConfetti(cx, cz) {
    partyUntil = clock + 14; confetti.visible = true;
    for (const c of conf) { c.p.set(cx + rand(-6, 6), rand(4, 9), cz + rand(-4, 4)); c.v.set(rand(-0.4, 0.4), rand(-1.6, -0.8), rand(-0.4, 0.4)); c.r.set(rand(0, 6), rand(0, 6), 0); }
  }
  const noteTex = canvasTex(64, 64, (g) => { g.clearRect(0, 0, 64, 64); g.fillStyle = '#fff'; g.font = '700 48px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('♪', 32, 34); });
  const notes = [];
  function emitNote(pos, hue) {
    const m = new THREE.SpriteMaterial({ map: noteTex, color: hsl(hue, 0.8, 0.65), transparent: true, depthWrite: false }); owned.add(m);
    const s = new THREE.Sprite(m); s.scale.setScalar(0.45); s.position.copy(pos); scene.add(s);
    notes.push({ s, t: 0, x0: pos.x, ph: Math.random() * 6 });
  }

  // ------------------------------------------------------------------ routes (doors, not walls)
  const NODES = {
    C: [0, 0.6, 'work'], WR: [-8, 0.6, 'work'], ER: [8, 0.6, 'work'], NR: [0, -3.5, 'work'], SE: [8, 7.6, 'work'], NG: [5.9, -4.2, 'work'],
    SWo: [-6, 9.6, 'work'], SEo: [6, 9.8, 'work'],
    DWi: [-13.2, 0.6, 'work'], DW: [-15, 0.6, 'hall'], WH: [-17.5, 0.25, 'hall'], WM: [-20, 0.25, 'hall'],
    SRd: [-20, -1, 'server'], SRi: [-20, -3.5, 'server'], PTd: [-20, 1.5, 'pantry'], PTi: [-20, 4, 'pantry'], PTe: [-17.3, 8.6, 'pantry'],
    DEi: [13.4, 7.6, 'work'], DE: [15, 7.6, 'meet'], MRi: [17.5, 7.6, 'meet'], MRs: [21, 4.5, 'meet'], MRw: [18.3, -2, 'meet'],
    MRe: [23.7, -2, 'meet'], MRnw: [18.3, -8.8, 'meet'], MRn: [21, -9.1, 'meet'],
    GRd: [-6, 11.6, 'game'], GRi: [-6, 13.2, 'game'], GRm: [-11, 13.4, 'game'], GRw: [-21, 13.4, 'game'], GRsw: [-21, 18.4, 'game'],
    GRs: [-14, 19.4, 'game'], GRe: [-3, 17, 'game'], GRx: [-1.2, 17, 'game'], GRtw: [-17.6, 16, 'game'], GRte: [-10.4, 16, 'game'],
    GDw: [0.8, 17, 'garden'], GDd: [6, 11.6, 'garden'], GDi: [6, 13.2, 'garden'], GDc: [12.5, 14.4, 'garden'], GDs: [9, 19.4, 'garden'],
    GDe: [19, 13.6, 'garden'], GDse: [19.5, 19.2, 'garden'],
  };
  const EDGES = [['C', 'WR'], ['C', 'ER'], ['C', 'NR'], ['NR', 'NG'], ['ER', 'NG'], ['WR', 'DWi'], ['DWi', 'DW'], ['DW', 'WH'], ['WH', 'WM'], ['WM', 'SRd'], ['SRd', 'SRi'],
    ['WM', 'PTd'], ['PTd', 'PTi'], ['PTi', 'PTe'], ['ER', 'SE'], ['SE', 'DEi'], ['DEi', 'DE'], ['DE', 'MRi'], ['MRi', 'MRs'], ['MRs', 'MRw'],
    ['MRs', 'MRe'], ['MRw', 'MRnw'], ['MRnw', 'MRn'],
    ['C', 'SWo'], ['WR', 'SWo'], ['C', 'SEo'], ['SE', 'SEo'], ['SWo', 'GRd'], ['GRd', 'GRi'], ['GRi', 'GRm'], ['GRm', 'GRte'], ['GRm', 'GRw'], ['GRw', 'GRtw'],
    ['GRw', 'GRsw'], ['GRsw', 'GRs'], ['GRs', 'GRtw'], ['GRs', 'GRte'], ['GRi', 'GRe'], ['GRs', 'GRe'], ['GRe', 'GRx'], ['GRx', 'GDw'],
    ['GDw', 'GDi'], ['GDw', 'GDs'], ['GDi', 'GDd'], ['GDd', 'SEo'], ['GDi', 'GDc'], ['GDc', 'GDe'], ['GDe', 'GDse'], ['GDs', 'GDse']];
  const adj = {};
  for (const [a, b] of EDGES) { (adj[a] = adj[a] || []).push(b); (adj[b] = adj[b] || []).push(a); }
  const nodeP = (id) => V(NODES[id][0], NODES[id][1]);
  const roomOf = (p) => (p.z > 11.55 ? (p.x < -1 ? 'game' : 'garden') : p.x < -15 ? (p.z < -1 ? 'server' : p.z > 1.5 ? 'pantry' : 'hall') : p.x > 15 ? 'meet' : 'work');
  const nearestNode = (p, room) => {
    let best = null, bd = Infinity;
    for (const [id, [x, z, r]] of Object.entries(NODES)) { if (r !== room) continue; const d = Math.hypot(p.x - x, p.z - z); if (d < bd) { bd = d; best = id; } }
    return best || 'C';
  };
  function path(a, b) {
    const dist = { [a]: 0 }, prev = {}, todo = new Set(Object.keys(NODES));
    while (todo.size) {
      let u = null; for (const n of todo) if (dist[n] !== undefined && (u === null || dist[n] < dist[u])) u = n;
      if (u === null || u === b) break;
      todo.delete(u);
      for (const v of adj[u] || []) { const d = dist[u] + nodeP(u).distanceTo(nodeP(v)); if (dist[v] === undefined || d < dist[v]) { dist[v] = d; prev[v] = u; } }
    }
    const out = []; for (let n = b; n; n = prev[n]) { out.unshift(n); if (n === a) break; }
    return out[0] === a ? out : [a, b];
  }
  let agents = {};
  const stationAt = (p) => Object.values(agents).find((x) => Math.hypot(x.home.x - p.x, x.home.z - p.z) < 0.9);
  /** Walking points from `from` to `to`: out round its own desk, along the route network, round the target desk. */
  function route(from, to) {
    const pre = [], post = [];
    let a0 = from, b0 = to;
    const sf = stationAt(from); if (sf) { pre.push(sf.sideOut, sf.sideFront); a0 = sf.sideFront; }
    const st = stationAt(to); if (st) { post.push(st.sideFront, st.sideOut); b0 = st.sideFront; }
    const ra = roomOf(a0), rb = roomOf(b0);
    const mid = ra === rb && !['work', 'garden', 'game'].includes(ra) ? [] : path(nearestNode(a0, ra), nearestNode(b0, rb)).map(nodeP);
    return [...pre, ...mid, ...post, to.clone()];
  }

  // ------------------------------------------------------------------ bake: merge static meshes that share a material
  // Hundreds of small props become a few dozen draw calls (each mesh is drawn again for shadows), which keeps the
  // office smooth on integrated graphics. Anything that moves or animates was marked with dyn() and stays separate.
  function bakeStatic() {
    scene.updateMatrixWorld(true);
    const groups = new Map(), victims = [];
    const isDyn = (o) => { for (let x = o; x; x = x.parent) if (x.userData.dyn) return true; return false; };
    scene.traverse((o) => {
      if (!o.isMesh || o.isInstancedMesh || o.isSkinnedMesh || Array.isArray(o.material) || isDyn(o)) return;
      const g = o.geometry, attrs = Object.keys(g.attributes).sort().join(',');
      if (!g.attributes.normal || !g.attributes.uv) return;
      const mat = o.material;
      // plain coloured materials that differ only in colour share one material with the colour baked into the vertices
      const tint = !mat.map && !mat.userData.unique && !mat.transparent && (mat.isMeshStandardMaterial);
      const sig = tint ? `tint|${mat.type}|${mat.roughness}|${mat.metalness}|${mat.emissive.getHex()}|${mat.emissiveIntensity}|${mat.clearcoat || 0}|${mat.sheen || 0}|${mat.side}` : mat.uuid;
      const key = `${sig}|${o.castShadow ? 1 : 0}|${o.receiveShadow ? 1 : 0}|${attrs}`;
      if (!groups.has(key)) groups.set(key, { mat, tint, cast: o.castShadow, recv: o.receiveShadow, geos: [] });
      let geo = g.index ? g.toNonIndexed() : g.clone();
      for (const n of Object.keys(geo.attributes)) if (!['position', 'normal', 'uv'].includes(n)) geo.deleteAttribute(n);
      if (tint) {
        const n = geo.attributes.position.count, col = new Float32Array(n * 3), c = mat.color;
        for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
        geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      }
      geo.applyMatrix4(o.matrixWorld);
      groups.get(key).geos.push(geo);
      victims.push(o);
    });
    for (const o of victims) o.parent.remove(o);
    let n = 0;
    for (const { mat, tint, cast, recv, geos } of groups.values()) {
      const merged = geos.length === 1 ? geos[0] : mergeGeometries(geos, false);
      if (!merged) continue;
      let useMat = mat;
      if (tint) { useMat = mat.clone(); useMat.color.set(0xffffff); useMat.vertexColors = true; owned.add(useMat); }
      const m = new THREE.Mesh(merged, useMat); m.castShadow = cast; m.receiveShadow = recv; m.matrixAutoUpdate = false;
      scene.add(m); n++;
      if (geos.length > 1) geos.forEach((g) => g.dispose());
    }
    scene.traverse((o) => { if (!isDyn(o) && o !== scene && !o.isLight) { o.matrixAutoUpdate = false; o.updateMatrix(); } });
    // the shadow map is drawn once, so anything that moves must not cast into it (its shadow would stay behind)
    scene.traverse((o) => { if (o.isMesh && isDyn(o)) o.castShadow = false; });
    return { meshes: victims.length, merged: n };
  }
  const baked = bakeStatic();

  // ------------------------------------------------------------------ robots
  const gltf = await new GLTFLoader().loadAsync(ROBOT_URL);
  const src = gltf.scene;
  const bbox = new THREE.Box3().setFromObject(src);
  const robotScale = ROBOT_HEIGHT / (bbox.max.y - bbox.min.y);
  const clips = Object.fromEntries(gltf.animations.map((a) => [a.name, a]));
  const ONCE = new Set(['Wave', 'Yes', 'No', 'ThumbsUp', 'Punch', 'Jump', 'Standing', 'Sitting', 'Death', 'WalkJump']);
  let speed = 1;
  let runActive = false;
  const pickables = [];
  const saved = loadSaved();
  let saveDirty = false;
  const faceTextures = [];

  // all nine robots share one skeleton, so their part shapes are identical: build each geometry once and share it
  const geoCache = new Map();
  const geo = (key, make) => { if (!geoCache.has(key)) geoCache.set(key, make()); return geoCache.get(key); };
  /**
   * Builds one character on the model's skeleton: the original low-poly meshes are hidden and parts are attached to the
   * bones (so every animation still drives them). The look is a machine, not a toy: a satin light-grey shell (head,
   * chest, pelvis, upper arms, thighs) over a dark graphite frame (neck, forearms, shins, hands), dark metal joints,
   * accents in the agent's colour, a glowing chest light, a face screen and the agent's own gear.
   */
  function styleRobot(model, s) {
    const shell = M(0xeceae6, { roughness: 0.42, metalness: 0.08 });
    const frame = M(0x343842, { roughness: 0.4, metalness: 0.55 });
    const accent = M(hsl(s.hue, 0.55, 0.52), { roughness: 0.36, metalness: 0.12 }, true);
    const joint = M(0x1f2228, { roughness: 0.32, metalness: 0.7 });
    const coreM = M(hsl(s.hue, 0.9, 0.62), { emissive: hsl(s.hue, 0.95, 0.6), emissiveIntensity: 2.4, roughness: 0.3 }, true);
    model.traverse((o) => { if (o.isMesh) { o.visible = false; o.userData.hidden = true; } });
    model.updateMatrixWorld(true);
    const bones = {};
    model.traverse((o) => { if (o.isBone) bones[o.name] = o; });
    const B = (n) => bones[n] || bones[n.replace(/([LR])$/, '.$1')];
    const at = (n) => B(n).getWorldPosition(new THREE.Vector3());
    const parts = [];
    const part = (mesh, bone) => { mesh.traverse((c) => { if (c.isMesh) { c.castShadow = false; c.receiveShadow = true; parts.push(c); } }); B(bone).attach(mesh); return mesh; };
    const unitSphere = geo('sphere', () => new THREE.SphereGeometry(1, 16, 12));
    /** a rounded limb from p0 to p1 */
    const limb = (p0, p1, r, m, bone, shrink = 0) => {
      const dir = p1.clone().sub(p0), len = Math.max(0.05, dir.length() - shrink * 2);
      const body = Math.max(0.01, len - r * 2);
      const g = new THREE.Mesh(geo(`cap|${r}|${body.toFixed(3)}`, () => new THREE.CapsuleGeometry(r, body, 4, 12)), m);
      g.position.copy(p0).add(p1).multiplyScalar(0.5);
      g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
      return part(g, bone);
    };
    const ball = (p, r, m, bone, sc = [1, 1, 1]) => { const g = new THREE.Mesh(unitSphere, m); g.position.copy(p); g.scale.set(r * sc[0], r * sc[1], r * sc[2]); return part(g, bone); };

    // pelvis, abdomen, chest, belt, chest light, neck
    const hip = at('Hips'), neck = at('Neck'), headB = at('Head');
    ball(hip.clone().add(V3(0, 0.03, 0)), 1, shell, 'Body', [0.27, 0.14, 0.21]);
    ball(V3(0, 0.88, -0.03), 1, frame, 'Body', [0.23, 0.15, 0.19]);
    const torsoC = V3(0, 1.07, -0.03);
    ball(torsoC, 1, shell, 'Body', [0.36, 0.29, 0.27]);
    const belt = new THREE.Mesh(geo('belt', () => new THREE.TorusGeometry(1, 0.11, 10, 28)), accent);
    belt.rotation.x = Math.PI / 2; belt.scale.set(0.28, 0.22, 0.28); belt.position.set(0, 0.79, -0.03); part(belt, 'Body');
    const core = new THREE.Mesh(geo('core', () => new THREE.CircleGeometry(0.075, 24)), coreM); core.position.set(0, 1.12, torsoC.z + 0.262); core.rotation.x = -0.12;
    const coreRing = new THREE.Mesh(geo('coreRing', () => new THREE.TorusGeometry(0.09, 0.016, 8, 24)), accent); coreRing.position.copy(core.position); coreRing.rotation.x = -0.12;
    part(core, 'Body'); part(coreRing, 'Body');
    limb(neck.clone().add(V3(0, -0.04, 0)), headB.clone().add(V3(0, 0.06, 0)), 0.07, frame, 'Body');

    // arms: shell upper arm, graphite forearm and hand
    for (const side of ['L', 'R']) {
      const sh = at(`Shoulder${side}`), el = at(`LowerArm${side}`), wr = at(`Palm2${side}`), mid = at(`Middle1${side}`);
      ball(sh, 0.118, accent, `Shoulder${side}`);
      limb(at(`UpperArm${side}`), el, 0.09, shell, `UpperArm${side}`);
      ball(el, 0.078, joint, `LowerArm${side}`);
      limb(el, wr, 0.072, frame, `LowerArm${side}`, 0.02);
      const hand = new THREE.Mesh(unitSphere, frame);
      hand.position.copy(wr).lerp(mid, 0.45); hand.scale.set(0.11, 0.09, 0.125);
      hand.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), mid.clone().sub(wr).normalize());
      part(hand, `Palm2${side}`);
    }
    // legs: shell thigh, graphite shin, a solid shoe in the agent's colour
    for (const side of ['L', 'R']) {
      const th = at(`UpperLeg${side}`), kn = at(`LowerLeg${side}`), ft = at(`Foot${side}`);
      limb(th, kn, 0.118, shell, `UpperLeg${side}`);
      ball(kn, 0.092, joint, `LowerLeg${side}`);
      limb(kn, ft.clone().add(V3(0, 0.08, 0)), 0.085, frame, `LowerLeg${side}`, 0.01);
      const shoe = rbox(0.24, 0.14, 0.4, accent, 0.065); shoe.position.copy(ft).add(V3(0, 0.065, 0.08)); part(shoe, `Foot${side}`);
    }

    // head: a helmet with a face screen, ears and an antenna (a little smaller than before: less of a bobble-head)
    const rx = 0.34, ry = 0.29, rz = 0.31;
    const head = new THREE.Group();
    head.position.set(headB.x, headB.y + ry + 0.06, headB.z + 0.02);
    const helmet = new THREE.Mesh(geo('helmet', () => new THREE.SphereGeometry(1, 32, 22)), shell); helmet.scale.set(rx, ry, rz); head.add(helmet);
    const fc = document.createElement('canvas'); fc.width = 256; fc.height = 160;
    const faceTex = new THREE.CanvasTexture(fc); faceTex.colorSpace = THREE.SRGBColorSpace; faceTextures.push(faceTex);
    const faceM = new THREE.MeshStandardMaterial({ color: 0x07080b, roughness: 0.15, metalness: 0.3,
      emissive: hsl(s.hue, 0.85, 0.8), emissiveMap: faceTex, emissiveIntensity: 2.4 });
    owned.add(faceM);
    const visor = new THREE.Mesh(geo('visor', () => new THREE.SphereGeometry(1, 32, 18, Math.PI / 2 - 0.8, 1.6, Math.PI / 2 - 0.52, 1.02)), faceM);
    visor.scale.set(rx * 1.02, ry * 1.02, rz * 1.02); head.add(visor);
    for (const sx of [-1, 1]) {
      const ear = cyl(0.095, 0.095, 0.07, joint, 16); ear.rotation.z = Math.PI / 2; ear.position.set(sx * rx * 0.97, -0.01, -0.02); head.add(ear);
      const ring = new THREE.Mesh(geo('earRing', () => new THREE.TorusGeometry(0.066, 0.015, 6, 18)), coreM); ring.rotation.y = Math.PI / 2; ring.position.set(sx * (rx * 0.97 + 0.04), -0.01, -0.02); head.add(ring);
    }
    const antenna = new THREE.Group(); antenna.position.set(0.09, ry * 0.93, -0.05); head.add(antenna);
    const stalk = cyl(0.011, 0.015, 0.2, joint, 6); stalk.position.y = 0.1; antenna.add(stalk);
    const tipM = M(hsl(s.hue, 0.9, 0.62), { emissive: hsl(s.hue, 0.9, 0.62), emissiveIntensity: 2, roughness: 0.4 }, true);
    const tip = sphere(0.042, tipM, 10); tip.position.y = 0.22; antenna.add(tip);
    gear(s.gear, head, { rx, ry, rz, hue: s.hue });
    part(head, 'Head');
    // gear worn on the body (tie, bow tie, scarf, backpack, lanyard), around the chest
    const body = new THREE.Group(); body.position.set(0, neck.y, torsoC.z);
    if (bodyGear(s.gear, body, s.hue, 0.27)) part(body, 'Body');
    for (const p of parts) p.userData.gear = true;
    return { head, headBase: head.quaternion.clone(), faceTex, fc, tipM, antenna, hand: B('Palm2R'), accent, coreM, parts };
  }
  function gear(kind, head, { rx, ry, rz, hue }) {
    const add = (o, x, y, z) => { o.position.set(x, y, z); head.add(o); return o; };
    if (kind === 'glasses') {
      const fm = P(0x2b2b2f, { metalness: 0.7, roughness: 0.25 });
      for (const sx of [-1, 1]) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.095, 0.015, 8, 28), fm); add(r, sx * 0.125, 0.03, rz + 0.025); }
      add(box(0.07, 0.018, 0.018, fm), 0, 0.05, rz + 0.025);
      for (const sx of [-1, 1]) { const arm = box(0.018, 0.018, 0.3, fm); add(arm, sx * 0.22, 0.04, rz - 0.13); arm.rotation.y = sx * -0.28; }
    }
    if (kind === 'cap') {
      const cm = P(hsl(hue + 180, 0.62, 0.5), { roughness: 0.55, clearcoat: 0.2 });
      const crown = new THREE.Mesh(new THREE.SphereGeometry(1, 30, 14, 0, Math.PI * 2, 0, Math.PI / 2), cm); crown.scale.set(rx * 1.05, ry * 0.8, rz * 1.06); add(crown, 0, ry * 0.22, 0);
      const brim = cyl(0.24, 0.24, 0.025, cm, 28); brim.scale.set(1.15, 1, 1); add(brim, 0, ry * 0.3, rz * 0.82);
      add(sphere(0.03, cm, 8), 0, ry * 1.03, 0);
    }
    if (kind === 'fedora') {
      const fm = P(0x3b3530, { roughness: 0.65, clearcoat: 0.1 }), band = M(0x141414);
      const brim = cyl(rx * 1.45, rx * 1.45, 0.025, fm, 36); add(brim, 0, ry * 0.74, 0); brim.rotation.x = 0.06;
      add(cyl(rx * 0.8, rx * 0.9, 0.3, fm, 30), 0, ry * 0.74 + 0.16, 0);
      add(cyl(rx * 0.91, rx * 0.91, 0.06, band, 30), 0, ry * 0.74 + 0.05, 0);
    }
    if (kind === 'headphones') {
      const hm = P(0x1d1f26, { metalness: 0.5, roughness: 0.3 }), pad = P(hsl(hue, 0.6, 0.5));
      add(new THREE.Mesh(new THREE.TorusGeometry(rx * 1.07, 0.028, 8, 32, Math.PI), hm), 0, 0.02, -0.02);
      for (const sx of [-1, 1]) { const cup = cyl(0.13, 0.13, 0.11, pad, 28); cup.rotation.z = Math.PI / 2; add(cup, sx * (rx + 0.06), -0.01, -0.02); }
    }
    if (kind === 'crown') {
      const gold = P(0xf2c14e, { metalness: 0.9, roughness: 0.18, emissive: 0x6b4a10, emissiveIntensity: 0.3 });
      add(cyl(0.16, 0.16, 0.09, gold, 24, true), 0, ry + 0.01, 0);
      for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2; add(cyl(0, 0.042, 0.11, gold, 6), Math.cos(a) * 0.15, ry + 0.11, Math.sin(a) * 0.15); }
      for (let i = 0; i < 5; i++) { const a = (i + 0.5) / 5 * Math.PI * 2; add(sphere(0.02, glow(0xff4d6d, 0.8), 6), Math.cos(a) * 0.162, ry + 0.01, Math.sin(a) * 0.162); }
    }
    if (kind === 'headset') {
      const hm = P(0x2a2d35, { metalness: 0.5, roughness: 0.3 });
      add(new THREE.Mesh(new THREE.TorusGeometry(rx * 1.04, 0.02, 8, 32, Math.PI), hm), 0, 0.02, -0.02);
      const cup = cyl(0.11, 0.11, 0.07, hm, 24); cup.rotation.z = Math.PI / 2; add(cup, -(rx + 0.03), -0.01, -0.02);
      const boom = cyl(0.011, 0.011, 0.34, hm, 6); boom.rotation.x = Math.PI / 2; boom.rotation.y = 0.55; add(boom, -(rx - 0.05), -0.13, rz * 0.42);
      add(sphere(0.032, glow(hsl(hue, 0.9, 0.6), 1.2), 8), -0.2, -0.17, rz * 0.92);
    }
    if (kind === 'tie') add(cyl(0.011, 0.011, 0.15, M(0xffd23f), 6), rx * 0.92, ry * 0.45, 0.04).rotation.z = 0.6;   // a pencil behind the ear
  }
  /** Gear around the chest; `body` sits at the base of the neck, `fz` is the chest's front surface. */
  function bodyGear(kind, body, hue, fz) {
    const add = (o, x, y, z) => { o.position.set(x, y, z); body.add(o); return o; };
    if (kind === 'tie') {
      const tm = P(hsl(hue + 20, 0.7, 0.45), { roughness: 0.5 });
      add(rbox(0.09, 0.07, 0.05, tm, 0.02), 0, -0.06, fz - 0.04);
      const t = rbox(0.11, 0.34, 0.03, tm, 0.015); add(t, 0, -0.25, fz - 0.005); t.rotation.x = -0.18;
      return true;
    }
    if (kind === 'bowtie') {
      const bm = P(0xd2483d, { roughness: 0.4 });
      for (const sx of [-1, 1]) { const c = cyl(0, 0.08, 0.16, bm, 4); c.rotation.z = sx * Math.PI / 2; add(c, sx * 0.08, -0.06, fz - 0.05); }
      add(sphere(0.035, bm, 8), 0, -0.06, fz - 0.04);
      return true;
    }
    if (kind === 'scarf') {
      const sm = P(0xe0644a, { roughness: 0.9, clearcoat: 0, sheen: 1 });
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.07, 12, 28), sm); ring.rotation.x = Math.PI / 2; add(ring, 0, -0.02, 0);
      const tail = rbox(0.12, 0.32, 0.05, sm, 0.025); add(tail, 0.09, -0.2, fz - 0.03); tail.rotation.z = 0.12; tail.rotation.x = -0.2;
      return true;
    }
    if (kind === 'cap') {                             // the Scout's little backpack
      add(rbox(0.38, 0.42, 0.18, P(hsl(hue + 180, 0.5, 0.45), { roughness: 0.55 }), 0.07), 0, -0.3, -fz - 0.05);
      return true;
    }
    if (kind === 'headset') {                         // a lanyard with a badge
      const lm = M(hsl(hue, 0.6, 0.45));
      for (const sx of [-1, 1]) { const st = box(0.022, 0.3, 0.01, lm); add(st, sx * 0.07, -0.15, fz - 0.02); st.rotation.z = -sx * 0.25; st.rotation.x = -0.2; }
      add(rbox(0.14, 0.17, 0.02, P(0xffffff), 0.02), 0, -0.33, fz + 0.005).rotation.x = -0.15;
      return true;
    }
    return false;
  }
  const paddleM = P(0xd23c3c, { roughness: 0.5 });
  // a soft contact shadow under each robot (much cheaper than nine more shadow-casting skeletons)
  const blobTex = canvasTex(128, 128, (g, w) => { const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); gr.addColorStop(0, 'rgba(0,0,0,0.42)'); gr.addColorStop(0.55, 'rgba(0,0,0,0.2)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, w); });
  const blobMat = new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false }); owned.add(blobMat);
  const blobGeo = new THREE.PlaneGeometry(1.5, 1.5);

  const _yaw = new THREE.Quaternion(), _up = new THREE.Vector3(0, 1, 0);
  class Agent {
    constructor(s) {
      this.s = s; this.key = s.key;
      this.holder = new THREE.Group();
      const model = SkeletonUtils.clone(src);
      model.scale.setScalar(robotScale);
      this.holder.add(model);
      this.rig = styleRobot(model, s);
      for (const o of this.rig.parts) { o.userData.agentKey = s.key; pickables.push(o); }
      scene.add(this.holder);
      this.blob = new THREE.Mesh(blobGeo, blobMat); this.blob.rotation.x = -Math.PI / 2; this.blob.position.y = 0.03; this.blob.renderOrder = 1; scene.add(this.blob);
      this.mixer = new THREE.AnimationMixer(model);
      this.actions = {};
      for (const [n, c] of Object.entries(clips)) {
        const a = this.mixer.clipAction(c);
        if (ONCE.has(n)) { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }
        this.actions[n] = a;
      }
      this.cur = null;
      this.home = V(s.home[0], s.home[1]);
      this.faceAngle = Math.atan2(s.face[0], s.face[1]);
      this.holder.position.copy(this.home);
      this.holder.rotation.y = this.faceAngle;
      this.front = this.home.clone().add(V(s.face[0] * (s.front || 3.1), s.face[1] * (s.front || 3.1)));
      const side = V(s.face[1], -s.face[0]);
      this.sideOut = this.home.clone().add(side.clone().multiplyScalar(1.9));
      this.sideFront = this.front.clone().add(side.clone().multiplyScalar(1.9));
      this.queue = [];
      this.task = null;
      this.carry = new THREE.Group(); this.carry.position.set(0, 1.25, 0.62); this.carry.visible = false; this.holder.add(this.carry);
      this.carried = 0;
      this.seated = null;               // null | 'desk' | 'chair' | 'sofa' | 'swing'
      this.moveRate = 0;                // units/s while walking (drives the walk clip's speed), 0 when standing
      this.headYaw = 0;
      this.state = 'pending';
      this.nextIdle = rand(1, 6);
      this.convo = null;
      this.spot = null;
      this.scene = null;
      this.doing = '';
      this.expr = { name: null, until: 0 };
      this.mood = { joy: rand(0.5, 0.75), energy: rand(0.6, 1), stress: 0.1 };
      this.mem = (saved.mem[s.key] || []).slice(0, 10);
      this.lookTarget = null;
      this.look = 0;
      this.blinkAt = rand(1, 4); this.blinkUntil = 0;
      this.faceSig = '';
      this.glowK = 0;
      this.gestureUntil = 0;
      this.play('Idle');
    }
    play(name, fade = 0.25) {
      const next = this.actions[name]; if (!next) return 0;
      if (this.cur === next && !ONCE.has(name)) return next.getClip().duration;
      next.reset(); next.enabled = true; next.setEffectiveTimeScale(speed); next.setEffectiveWeight(1);
      if (this.cur) next.crossFadeFrom(this.cur, fade, false);
      next.play();
      this.cur = next;
      return next.getClip().duration / speed;
    }
    /** A short gesture while standing; the agent returns to Idle by itself. */
    gesture(name) { if (this.seated || !name || this.stunUntil) return; const d = this.play(name, 0.15); this.gestureUntil = clock + d * 0.92; }
    face(name, secs = 2.5) { this.expr = { name: exprName(name), until: clock + secs }; }
    feel(dj = 0, de = 0, ds = 0) { const m = this.mood; m.joy = clamp(m.joy + dj, 0, 1); m.energy = clamp(m.energy + de, 0, 1); m.stress = clamp(m.stress + ds, 0, 1); }
    /** Remember something (a real work event, a game, a prank). Memories pass on in conversations. */
    remember(text, from = null, kind = 'work') {
      if (!text) return false;
      if (this.mem.some((m) => m.text === text)) return false;
      this.mem.unshift({ text, from, kind, at: Date.now() });
      this.mem.length = Math.min(this.mem.length, 10);
      saved.mem[this.key] = this.mem; saveDirty = true;
      return true;
    }
    setCarry(n) {
      this.carried = Math.max(0, n);
      const want = Math.min(6, this.carried);
      while (this.carry.children.length < want) { const p = new THREE.Mesh(paperGeo, paperM); p.position.y = this.carry.children.length * 0.035; p.rotation.y = (Math.random() - 0.5) * 0.25; this.carry.add(p); }
      while (this.carry.children.length > want) this.carry.remove(this.carry.children[this.carry.children.length - 1]);
      this.carry.visible = this.carried > 0;
    }
    atHome() { return Math.hypot(this.holder.position.x - this.home.x, this.holder.position.z - this.home.z) < 0.6; }
    get hasWork() { return (this.task && !this.task.idle) || this.queue.some((t) => !t.idle); }
    get busy() { return !!this.task || this.queue.length > 0; }
    push(...tasks) { this.queue.push(...tasks); }
    pushIdle(...tasks) { for (const t of tasks) t.idle = true; this.queue.push(...tasks); }
    /** Work has arrived: drop any break plans and walk back to the desk first. */
    prepWork() {
      const wasWorking = this.hasWork;
      const hadIdle = this.queue.some((t) => t.idle) || (this.task && this.task.idle);
      this.queue = this.queue.filter((t) => !t.idle);
      if (this.task && this.task.idle) { this.task = null; this.play('Idle', 0.2); }
      if (this.convo) { this.convo.cancelled = true; this.convo = null; }
      if (this.meeting) { this.meeting.cancelled = true; this.meeting = null; }
      if (this.scene) { this.scene.cancel(); }
      if (this.spot) { this.spot.busy = false; this.spot = null; }
      this.lookTarget = null; this.doing = '';
      this.holder.rotation.x = 0;
      // an agent already busy with a work scene finishes it (scenes end at the desk); one on a break walks back first
      if (!wasWorking && (hadIdle || !this.atHome() || (this.seated && this.seated !== 'desk'))) {
        const back = [];
        if (this.seated && this.seated !== 'desk') back.push(T.stand());
        if (!this.atHome()) back.push(T.go(() => this.home), T.faceHome());
        this.queue.unshift(...back);
      }
    }
    baseExpr() {
      if (this.doing === 'napping') return 'sleepy';
      const m = this.mood;
      if (this.hasWork || (this.seated === 'desk' && runActive)) return m.stress > 0.65 ? 'angry' : 'focused';
      if (m.energy < 0.2) return 'tired';
      if (m.joy > 0.8) return 'happy';
      if (m.joy < 0.25) return 'sad';
      return 'neutral';
    }
    drawFace(dt) {
      const want = clock < this.expr.until ? this.expr.name : this.baseExpr();
      if (clock > this.blinkAt) { this.blinkUntil = clock + 0.13; this.blinkAt = clock + rand(2.2, 5.5); }
      let lk = 0;
      if (this.lookTarget) {
        const p = typeof this.lookTarget === 'function' ? this.lookTarget() : this.lookTarget;
        if (p) {
          let d = Math.atan2(p.x - this.holder.position.x, p.z - this.holder.position.z) - this.holder.rotation.y;
          d = Math.atan2(Math.sin(d), Math.cos(d));
          lk = clamp(d / 0.9, -1, 1);
        }
      }
      this.look += (lk - this.look) * Math.min(1, dt * 6);
      const sig = `${want}|${clock < this.blinkUntil ? 1 : 0}|${Math.round(this.look * 5)}`;
      if (sig === this.faceSig) return;
      this.faceSig = sig;
      drawFace(this.rig.fc.getContext('2d'), 256, 160, want, clock < this.blinkUntil, Math.round(this.look * 5) / 5);
      this.rig.faceTex.needsUpdate = true;
    }
    update(dt) {
      if (!this.task && this.queue.length) { this.task = this.queue.shift(); if (this.task.start) this.task.start(this); }
      if (this.task && this.task.update(this, dt)) this.task = null;
      if (!this.task && !this.queue.length) this.rest();
      // slapstick: a shove pushes back a step; a bonk knocks the robot over for a moment
      if (this.hitAt && clock >= this.hitAt) {
        const kind = this.hitKind; this.hitAt = 0;
        if (this.seated) this.face(kind === 'bonk' ? 'dizzy' : 'surprised', 2);
        else {
          this.knock = { dir: this.hitDir, left: kind === 'bonk' ? 0.3 : 0.22, v: 2.3 };
          if (kind === 'bonk') { this.gestureUntil = 0; this.play('Death', 0.12); this.face('dizzy', 3.4); this.stunUntil = clock + 2.6; }
          else this.face('surprised', 1.6);
        }
        this.feel(-0.04, 0, 0.08);
      }
      if (this.knock) { const k = this.knock; this.holder.position.addScaledVector(k.dir, k.v * Math.min(k.left, dt)); k.left -= dt; if (k.left <= 0) this.knock = null; }
      if (this.stunUntil && clock >= this.stunUntil) { this.stunUntil = 0; const d = this.play('Standing', 0.2); this.gestureUntil = clock + d * 0.9; }
      if (this.gestureUntil && clock > this.gestureUntil) {
        this.gestureUntil = 0;
        if (!this.seated && this.cur && ONCE.has(this.cur.getClip().name)) this.play('Idle', 0.3);
      }
      this.drawFace(dt);
      // the antenna sways while walking and its tip pulses while working
      const moving = this.cur === this.actions.Walking || this.cur === this.actions.Running;
      this.rig.antenna.rotation.x = Math.sin(clock * (moving ? 12 : 2)) * (moving ? 0.22 : 0.05);
      this.rig.tipM.emissiveIntensity = this.hasWork ? 2 + Math.sin(clock * 8) * 1.2 : 1.4;
      const g = selected === this.key ? 0.32 : hovered === this.key ? 0.2 : 0;
      this.glowK += (g - this.glowK) * Math.min(1, dt * 8);
      this.rig.accent.emissive.copy(hsl(this.s.hue, 0.7, 0.5)).multiplyScalar(this.glowK);
      this.mixer.update(dt);
      // the head turns a little toward whatever the eyes look at (on top of the animation)
      this.headYaw += (this.look * 0.45 - this.headYaw) * Math.min(1, dt * 5);
      this.rig.head.quaternion.copy(this.rig.headBase).multiply(_yaw.setFromAxisAngle(_up, this.headYaw));
      this.blob.visible = this.holder.visible;
      this.blob.position.x = this.holder.position.x; this.blob.position.z = this.holder.position.z;
      this.blob.position.y = this.seated ? 0.03 : 0.03 + Math.max(0, this.holder.position.y);
    }
    /** Sit on a seat whose centre is `pos` and top is `h` high, facing `ang`: hips on the seat, not in it. */
    sitOn(kind, pos, ang, h = SEAT_H[kind] || SEAT_H.chair) {
      this.holder.position.set(pos.x + Math.sin(ang) * SIT_FWD, Math.max(0, h - SIT_DROP), pos.z + Math.cos(ang) * SIT_FWD);
      this.holder.rotation.set(0, ang, 0);
      this.seated = kind;
      this.play('Sitting', 0.35);
    }
    /** The centre of this agent's own desk chair. */
    deskSeat() { return this.home.clone().add(V(-this.s.face[0] * 0.25, -this.s.face[1] * 0.25)); }
    // nothing queued: during a search, agents whose part has not started wait at their desk
    rest() {
      const wantDesk = runActive && this.state === 'pending';
      if (wantDesk) {
        if (!this.atHome()) { this.prepWork(); return; }
        if (this.seated !== 'desk') this.sitOn('desk', this.deskSeat(), this.faceAngle);
        return;
      }
      if (this.seated === 'desk' && runActive) { this.push(T.stand()); return; }
      this.doing = this.seated ? this.doing : '';
      if (!this.seated && (!this.cur || (this.cur !== this.actions.Idle && !this.cur.isRunning()))) this.play('Idle');
    }
  }

  // ------------------------------------------------------------------ tasks: small steps of a scene
  let focus = null, focusUntil = 0, clock = 0;
  let hovered = null, selected = null;

  // ------------------------------------------------------------------ fresh lines (kept in this browser between visits)
  const RECENT_KEEP = 160;
  saved.said = saved.said || [];
  saved.seen = saved.seen || [];
  const recentSaid = new Set(saved.said);
  function noteSaid(text) {
    if (!text || recentSaid.has(text)) return;
    saved.said.push(text); recentSaid.add(text);
    while (saved.said.length > RECENT_KEEP) recentSaid.delete(saved.said.shift());
    saveDirty = true;
  }
  /** A line from `arr` nobody has said lately — or, when all were, the one said longest ago. */
  function fresh(arr) {
    const opts = arr.filter((t) => !recentSaid.has(t));
    if (opts.length) return pick(opts);
    return arr.slice().sort((x, y) => saved.said.indexOf(x) - saved.said.indexOf(y))[0];
  }
  const sayOut = onSay;
  const lastWork = new Map();       // agent|line -> clock: the same work line from the same agent shows once a minute at most
  onSay = (key, text, secs, kind = 'work') => {
    if (kind === 'work') {
      const k = `${key}|${text}`, t = lastWork.get(k);
      if (t !== undefined && clock - t < 60) return;
      if (lastWork.size > 400) lastWork.clear();
      lastWork.set(k, clock);
    } else if (kind !== 'think' && kind !== 'memory') noteSaid(text);
    sayOut(key, text, secs, kind);
  };
  const val = (x, a) => (typeof x === 'function' ? x(a) : x);
  const T = {
    /** walk through `points` (array, or a function returning a destination that is routed when the walk starts) */
    walkTo(points, run = false, direct = false, sneak = false) {
      let pts = Array.isArray(points) ? points.map((p) => p.clone()) : null;
      return {
        start(a) {
          if (!pts) { const d = points(); pts = direct ? [d.clone()] : route(a.holder.position, d); }
          a.seated = null; a.holder.rotation.x = 0; a.play(run ? 'Running' : 'Walking', 0.2);
          a.moveRate = run ? RUN_SPEED : sneak ? SNEAK_SPEED : WALK_SPEED;
          if (sneak) a.holder.rotation.x = 0.16;
        },
        update(a, dt) {
          const target = pts[0];
          if (!target) {
            if (sneak) a.holder.rotation.x = 0;
            a.moveRate = 0;
            a.play('Idle', 0.25); return true;
          }
          const pos = a.holder.position;
          let dx = target.x - pos.x, dz = target.z - pos.z;
          const dist = Math.hypot(dx, dz);
          const step = a.moveRate * speed * dt;
          if (dist <= Math.max(step, 0.05)) { pos.set(target.x, 0, target.z); pts.shift(); return false; }
          let sx = 0, sz = 0;
          for (const o of list) {
            if (o === a || !o.holder.visible) continue;
            const ox = pos.x - o.holder.position.x, oz = pos.z - o.holder.position.z, d = Math.hypot(ox, oz);
            if (d > 0.01 && d < 1.0) { sx += (ox / d) * (1.0 - d); sz += (oz / d) * (1.0 - d); }
          }
          dx = dx / dist + sx * 0.8; dz = dz / dist + sz * 0.8;
          const n = Math.hypot(dx, dz) || 1;
          pos.x += (dx / n) * step; pos.z += (dz / n) * step; pos.y = 0;
          turnTo(a, Math.atan2(dx, dz), dt * 10);
          return false;
        },
      };
    },
    go(dest, run = false) { return T.walkTo(dest, run); },
    sneak(dest) { return T.walkTo(dest, false, false, true); },
    faceAgent(other) { return { start(a) { a.lookTarget = () => other.holder.position; }, update(a, dt) { const p = other.holder.position; return turnTo(a, Math.atan2(p.x - a.holder.position.x, p.z - a.holder.position.z), dt * 8); } }; },
    faceAngle(ang) { return { update(a, dt) { return turnTo(a, val(ang, a), dt * 8); } }; },
    faceHome() { return { update(a, dt) { return turnTo(a, a.faceAngle, dt * 8); } }; },
    anim(name) { let left = 0; return { start(a) { const n = val(name, a); left = n ? a.play(n, 0.2) * 0.95 : 0; }, update(a, dt) { left -= dt; if (left <= 0) { if (!a.seated) a.play('Idle', 0.3); return true; } return false; } }; },
    loop(name, secs) { let left = secs; return { start(a) { a.play(name, 0.3); }, update(a, dt) { left -= dt * speed; if (left <= 0) { a.play('Idle', 0.3); return true; } return false; } }; },
    wait(secs) { let left = 0; return { start(a) { left = val(secs, a); }, update(a, dt) { left -= dt * speed; return left <= 0; } }; },
    say(text, secs = 3.6, kind = 'work') { return { start(a) { const t = val(text, a); if (t) onSay(a.key, t, secs / speed, kind); }, update() { return true; } }; },
    face(expr, secs = 2.5) { return { start(a) { a.face(val(expr, a), secs); }, update() { return true; } }; },
    call(fn) { return { start(a) { fn(a); }, update() { return true; } }; },
    until(cond, timeout = 10) { let t = 0; return { update(a, dt) { t += dt; return cond() || t > timeout; } }; },
    focus(fn) { return { start(a) { focus = fn(a); focusUntil = clock + 6; }, update() { return true; } }; },
    /** turn to face the way the seat faces, then sit down on it (h: the seat's top; default by kind) */
    sit(kind, pos, ang, h) {
      return { update(a, dt) { if (!turnTo(a, ang, dt * 10)) return false; a.sitOn(kind, pos, ang, h); return true; } };
    },
    /** walk to just in front of a seat, turn and sit: the robot never walks into the furniture */
    goSit(kind, spotOrPos, ang, h) {
      const pos = spotOrPos.pos || spotOrPos, face = ang ?? spotOrPos.face ?? 0, top = h ?? spotOrPos.h;
      const front = () => V(pos.x + Math.sin(val(face)) * SIT_FWD, pos.z + Math.cos(val(face)) * SIT_FWD);
      return [T.go(front), { update(a, dt) { const f = val(face); if (!turnTo(a, f, dt * 10)) return false; a.sitOn(kind, pos, f, top); return true; } }];
    },
    stand() {
      let left = 0, dur = 0, y0 = 0;
      return {
        start(a) { a.holder.rotation.x = 0; y0 = a.holder.position.y; dur = left = a.seated ? a.play('Standing', 0.25) * 0.9 : 0; a.seated = null; if (!dur) a.holder.position.y = 0; },
        update(a, dt) { left -= dt; a.holder.position.y = dur > 0 ? y0 * Math.max(0, left / dur) : 0; return left <= 0; },
      };
    },
    doing(label) { return { start(a) { a.doing = label; }, update() { return true; } }; },
  };
  function turnTo(a, ang, k) {
    let d = ang - a.holder.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    if (Math.abs(d) < 0.03) { a.holder.rotation.y = ang; return true; }
    a.holder.rotation.y += d * Math.min(1, k);
    return false;
  }
  function throwPaper(from, to, onLand) {
    const p = new THREE.Mesh(paperGeo, paperM); scene.add(p);
    flying.push({ p, from: from.clone(), to: to.clone(), t: 0, d: 0.7, onLand });
  }
  const worldPos = (obj) => obj.getWorldPosition(new THREE.Vector3());

  agents = Object.fromEntries(STATIONS.map((s) => [s.key, new Agent(s)]));
  const list = Object.values(agents);
  const nameOf = (k) => (agents[k] ? agents[k].s.name : k);

  // ------------------------------------------------------------------ friendships (this browser)
  const relKey = (a, b) => [a, b].sort().join('|');
  const rel = (a, b) => { const k = relKey(a.key, b.key); saved.rel[k] = saved.rel[k] || { chats: 0, wins: {} }; return saved.rel[k]; };
  function bond(a, b, n = 1) { rel(a, b).chats += n; saveDirty = true; }
  function friendsOf(a) {
    let best = null, rival = null;
    for (const o of list) {
      if (o === a) continue;
      const r = saved.rel[relKey(a.key, o.key)]; if (!r) continue;
      const games = (r.wins[a.key] || 0) + (r.wins[o.key] || 0);
      const score = r.chats + games * 1.5;
      if (score > 0 && (!best || score > best.score)) best = { key: o.key, name: o.s.name, score };
      if (games >= 2 && (!rival || games > rival.games)) rival = { key: o.key, name: o.s.name, games, rec: `${r.wins[a.key] || 0}–${r.wins[o.key] || 0}` };
    }
    return { best, rival };
  }

  // ------------------------------------------------------------------ work scenes (real events only)
  function handoff(fromKey, toKey, n, lineA, lineB) {
    const A = agents[fromKey], B = agents[toKey];
    A.prepWork(); B.prepWork();
    const meet = B.front.clone();
    const dir = A.front.clone().sub(meet); dir.y = 0; if (dir.lengthSq() < 0.01) dir.set(1, 0, 0); dir.normalize();
    const spotA = meet.clone().add(dir.clone().multiplyScalar(0.8));
    const spotB = meet.clone().sub(dir.clone().multiplyScalar(0.8));
    const sync = { aReady: false, bReady: false, done: false };
    A.push(
      T.call((a) => { a.setCarry(n); setPile(fromKey, stations[fromKey].count - n); }),
      T.focus(() => meet),
      T.say(lineA),
      T.walkTo([A.sideOut, A.sideFront, spotA]),
      T.call(() => { sync.aReady = true; }),
      T.until(() => sync.bReady),
      T.faceAgent(B),
      T.anim('Yes'),
      T.call((a) => { const from = worldPos(a.carry); const to = worldPos(B.holder).setY(1.3); a.setCarry(0); throwPaper(from, to, () => { B.setCarry(n); }); }),
      T.wait(0.6),
      T.call((a) => { sync.done = true; a.lookTarget = null; }),
      T.walkTo([A.sideFront, A.sideOut, A.home]),
      T.faceHome(),
    );
    B.push(
      T.walkTo([B.sideOut, B.sideFront, spotB]),
      T.call(() => { sync.bReady = true; }),
      T.until(() => sync.aReady),
      T.faceAgent(A),
      T.anim('Wave'),
      T.until(() => sync.done, 6),
      T.face('happy', 2),
      T.say(lineB),
      T.anim('ThumbsUp'),
      T.call((b) => { b.lookTarget = null; }),
      T.walkTo([B.sideFront, B.sideOut, B.home]),
      T.faceHome(),
      T.call((b) => { const got = b.carried; b.setCarry(0); setPile(toKey, stations[toKey].count + got); }),
    );
  }
  let portalFlash = 0, stampHit = 0, serverBusy = 0;
  /** web search: through the portal. Company boards: a run to the server room racks. */
  function scoutTrip(line, found, toServers) {
    const S = agents.discover; S.prepWork();
    if (toServers) {
      const rackSpot = V(-20.2 + rand(-1.6, 1.6), -8.4);
      S.push(T.focus(() => rackSpot), T.say(short(line, 60)), T.go(() => rackSpot, true), T.faceAngle(Math.PI),
        T.call(() => { serverBusy = 2.2; }), T.anim('Yes'), T.call((a) => a.setCarry(Math.max(1, found))),
        T.go(() => S.home, true), T.faceHome(), T.call((a) => { const n = a.carried; a.setCarry(0); setPile('discover', stations.discover.count + n); }));
      return;
    }
    const portal = stations.discover.portal;
    const gate = worldPos(portal.arch).setY(0).add(V(0, 0.9));
    const inside = gate.clone().add(V(0, -1.6));
    S.push(
      T.focus(() => gate),
      T.say(short(line, 60)),
      T.walkTo([S.sideOut, gate], true),
      T.walkTo([inside], true),
      T.call((a) => { a.holder.visible = false; portalFlash = 1; }),
      T.wait(1.1),
      T.call((a) => { a.holder.visible = true; portalFlash = 1; a.setCarry(Math.max(1, found)); }),
      T.walkTo([gate, S.sideOut, S.home], true),
      T.faceHome(),
      T.call((a) => { const n = a.carried; a.setCarry(0); setPile('discover', stations.discover.count + n); }),
    );
  }

  let lastId = null, celebrated = false, runId;
  let stateMap = {};
  const world = { scoredRatio: 0, counts: {}, status: '', total: 0, top: '' };
  function queueLoad() { return list.reduce((n, a) => n + a.queue.filter((t) => !t.idle).length, 0); }
  function passToNext(fromKey, toKey, toBin) {
    const st = stations[fromKey];
    setPile(fromKey, st.count - 1);
    if (toBin) throwPaper(worldPos(st.pile), worldPos(st.bin).setY(0.7), () => addToBin(fromKey));
    else throwPaper(worldPos(st.pile), worldPos(stations[toKey].pile), () => setPile(toKey, stations[toKey].count + 1));
  }
  const work = (key, ...tasks) => { const a = agents[key]; a.prepWork(); a.push(...tasks); };
  const workFeel = (key, dj, ds) => { const a = agents[key]; a.feel(dj, -0.015, ds); };

  function onEvent(it) {
    const msg = it.message || '';
    const k = it.kind;
    const job = it.job || {};
    switch (it.stage) {
      case 'understand':
        if (k === 'work') work('understand', T.say(short(msg, 64)), T.anim('Yes'));
        else if (k === 'good') {
          agents.understand.remember(short(msg, 90));
          setPile('understand', 1); handoff('understand', 'plan', 1, 'Here is who we are searching for', 'Thanks — planning the searches now');
        }
        break;
      case 'plan':
        if (k === 'work') work('plan', T.say(short(msg, 64)), T.anim('Wave'));
        else if (k === 'info' && /planned/.test(msg)) {
          const n = (/(\d+) searches planned/.exec(msg) || [])[1];
          agents.plan.remember(short(msg, 90));
          setPile('plan', 1); handoff('plan', 'discover', 1, `Here is the plan${n ? `: ${n} searches` : ''}`, 'On it — heading out to look!');
        }
        break;
      case 'discover': {
        const S = agents.discover;
        if (k === 'work' && S.queue.length < 12) {
          const board = /Opening (.+?)'s careers board/.exec(msg);
          const boards = /job boards/.test(msg);
          if (board) S.remember(`Checked ${board[1]}'s own job board`);
          scoutTrip(board ? `Checking ${board[1]}'s own job board` : msg, board ? 2 : 3, !!(board || boards));
          workFeel('discover', 0.01, 0.01);
        } else if (k === 'good' || k === 'info') work('discover', T.say(short(msg, 70)));
        break;
      }
      case 'normalize': {
        const R = agents.normalize;
        if (k === 'work') handoff('discover', 'normalize', Math.max(2, stations.discover.count), `Here are the ${stations.discover.count || ''} job posts I found`.replace('  ', ' '), 'Great — I will open every page');
        else if (/^Read /.test(msg) && R.queue.length < 10) { work('normalize', T.face('focused', 3), T.say(`Reading “${short(titleOf(msg), 34)}”`), T.anim('Yes')); workFeel('normalize', 0, 0.01); }
        else if (k === 'info' && R.queue.length < 10) work('normalize', T.say(short(msg, 70)));
        break;
      }
      case 'dedupe':
        if (k === 'work') handoff('normalize', 'dedupe', Math.max(2, stations.normalize.count), 'All the postings, read and ready', 'Let me merge the duplicates');
        else { agents.dedupe.remember(short(msg, 90)); work('dedupe', T.face('proud', 2.5), T.say(short(msg, 70)), T.anim('ThumbsUp')); }
        break;
      case 'validate': {
        const Vf = agents.validate;
        if (k === 'work') {
          if (!Vf.handed) { Vf.handed = true; handoff('dedupe', 'validate', Math.max(2, stations.dedupe.count), 'Unique jobs — please check they are real', 'Checking each one is live'); }
          work('validate', T.say(short(msg, 64)));
        } else if (Vf.queue.length < 16) {
          const t = short(titleOf(msg) || msg.replace(/ (is live|has closed|looks old).*$/, ''), 34);
          if (k === 'good') { work('validate', T.anim('Punch'), T.call(() => { stampHit = 1; passToNext('validate', 'match'); }), T.say(`✓ ${t} is live`, 2.6)); workFeel('validate', 0.02, -0.01); }
          else if (k === 'reject') {
            Vf.remember(job.title ? `Binned “${short(job.title, 36)}” at ${job.company} — ${/closed/.test(msg) ? 'closed' : 'not a real posting'}` : short(msg, 80));
            work('validate', T.call((a) => a.face(pick(['angry', 'sad']), 2)), T.anim('No'), T.call(() => passToNext('validate', 'match', true)), T.say(`✗ ${short(msg, 46)}`, 2.6));
            workFeel('validate', -0.02, 0.04);
          } else work('validate', T.say(short(msg, 56), 2.6), T.call(() => passToNext('validate', 'match')));
        }
        break;
      }
      case 'extract':
        gateAnalyst();
        if (k === 'work' && agents.match.queue.length < 12) work('match', T.face('focused', 3), T.say(`Reading what “${short(titleOf(msg) || 'this job', 28)}” asks for`), T.anim('Yes'));
        break;
      case 'match': {
        gateAnalyst();
        const A = agents.match;
        if (A.queue.length > 16) break;
        const fit = /^(Strong match|Good match|Stretch)/.test(msg);
        const bad = /^Not a fit/.test(msg) || k === 'reject';
        if (fit) {
          const title = titleOf(msg) || (msg.split('·')[1] || '').trim();
          if (/^(Strong|Good)/.test(msg) && title) { world.top = short(title, 40); A.remember(`Great fit: ${short(title, 50)}`); agents.rank.remember(`Ranked “${short(title, 40)}” near the top`); }
          work('match', T.call((a) => a.face(/^Strong/.test(msg) ? 'love' : 'happy', 2.4)), T.anim('ThumbsUp'), T.say(short(msg, 70), 3));
          handoff('match', 'rank', 1, `“${short(title || 'This one', 30)}” fits you!`, 'Adding it to your results');
          agents.rank.push(T.call(() => addResultCard()));
          workFeel('match', 0.05, -0.01);
        } else if (bad) {
          work('match', T.call((a) => a.face('sad', 2)), T.anim('No'), T.say(short(msg, 70), 3), T.call(() => passToNext('match', null, true)));
          workFeel('match', -0.01, 0.02);
        } else work('match', T.say(short(msg, 70), 3));
        break;
      }
      case 'rank':
        if (k === 'done') { agents.rank.remember(short(msg, 90)); celebrate(msg); }
        break;
      case 'connect': {
        const C = agents.connect;
        if (k === 'work' && !C.handed) {
          C.handed = true;
          handoff('rank', 'connect', 2, 'Our top matches — find us a way in!', 'On it — I know people everywhere');
        }
        if (k === 'work' && job.company && C.queue.length < 12) {
          work('connect', T.face('focused', 3), T.say(`Finding people at ${short(job.company, 30)}…`, 3), T.anim('Yes'));
        } else if (k === 'good') {
          C.remember(`Found a way in at ${short(job.company || 'a top company', 30)} — referral note ready`);
          work('connect', T.call((a) => { a.face('happy', 2.5); launchPlane(worldPos(stations.connect.desk).setY(1.3)); }), T.anim('ThumbsUp'), T.say(short(msg, 70), 3));
          workFeel('connect', 0.04, 0);
        } else if (k === 'done') {
          C.remember(short(msg, 90));
          work('connect', T.face('proud', 3), T.say(short(msg, 80), 4), T.anim('Wave'));
        }
        break;
      }
      default:
    }
  }
  function gateAnalyst() {
    const A = agents.match;
    if (A.gated) return;
    A.gated = true;
    A.prepWork();
    A.push(T.until(() => !agents.validate.hasWork, 45));
  }
  let reviewAt = 0, partyAt = 0;
  function celebrate(msg) {
    if (celebrated) return; celebrated = true;
    const R = agents.rank;
    let cheered = false;
    R.prepWork();
    // wait for real work only: the others' "cheer for the Ranker" steps are not work (waiting on them deadlocked)
    const working = (a) => (a.task && !a.task.idle && !a.task.cheer) || a.queue.some((t) => !t.idle && !t.cheer);
    R.push(T.until(() => !working(agents.match) && !working(agents.validate) && !working(agents.dedupe), 90),
      T.focus(() => R.front.clone()), T.call((a) => { cheered = true; a.face('proud', 6); a.feel(0.2, 0, -0.2); }), T.say(short(msg, 80), 6), T.loop('Dance', 5));
    let i = 0;
    for (const a of list) {
      if (a === R) continue;
      a.prepWork();
      const steps = [T.until(() => cheered, 120), T.stand(), T.wait(0.4 + (i++) * 0.25), T.call((x) => { x.face(pick(['happy', 'laugh', 'love']), 3); x.feel(0.1, 0, -0.1); }), T.anim(i % 2 ? 'Wave' : 'ThumbsUp')];
      for (const t of steps) t.cheer = true;
      a.push(...steps);
    }
    reviewAt = clock + 22;                     // then everyone meets to look at the results together
    const envious = pick(list.filter((a) => a !== R && a.key !== 'connect'));
    if (envious) envious.jealous = { key: R.key, until: clock + 400 };
  }
  function reset(newRun) {
    runId = newRun; celebrated = false; lastId = null; world.top = ''; reviewAt = 0; partyAt = 0;
    for (const a of list) {
      if (a.scene) a.scene.cancel();
      a.queue.length = 0; a.task = null; a.setCarry(0); a.handed = false; a.gated = false; a.holder.visible = true;
      if (a.convo) a.convo.cancelled = true; a.convo = null;
      if (a.meeting) a.meeting.cancelled = true; a.meeting = null;
      if (a.spot) a.spot.busy = false; a.spot = null;
      a.seated = null; a.doing = ''; a.lookTarget = null; a.holder.rotation.x = 0; a.holder.position.y = 0; a.moveRate = 0; a.play('Idle', 0.1);
      if (!a.atHome()) a.push(T.go(() => a.home), T.faceHome());
    }
    for (const k of Object.keys(stations)) { setPile(k, 0); if (stations[k].bin) { stations[k].bin.clear(); stations[k].binCount = 0; } }
    stations.rank.cards.clear();
  }

  // ------------------------------------------------------------------ office life (breaks, chats, games, meetings)
  const SPOTS = {
    pantryTable: [{ pos: V(-21.25, 7.2), seat: true, face: Math.PI / 2, h: STOOL_H }, { pos: V(-18.75, 7.2), seat: true, face: -Math.PI / 2, h: STOOL_H }],
    cooler: [{ pos: V(-16.6, 9.3) }, { pos: V(-17.9, 10.2) }],
    sofa: [{ pos: V(-21.7, 10.75), seat: true, face: Math.PI, h: SEAT_H.sofa }, { pos: V(-20.3, 10.75), seat: true, face: Math.PI, h: SEAT_H.sofa }],
    lounge: [{ pos: V(23.2, 7.4) }, { pos: V(24.6, 7.0) }],
    floorA: [{ pos: V(-3.6, 3.4) }, { pos: V(-2.2, 3.4) }],
    floorB: [{ pos: V(3.4, 5.0) }, { pos: V(4.8, 5.0) }],
    window: [{ pos: V(5.3, -9.5) }, { pos: V(6.5, -9.3) }],
    garden: [{ pos: V(17.2, 14.6) }, { pos: V(18.5, 15.2) }],
    gameNook: [{ pos: V(-9.3, 13.3) }, { pos: V(-8.0, 13.8) }],
    bench: benchSpots,
    bags: bagSpots,
  };
  const COFFEE = { pos: V(-23.45, 4.4), face: -Math.PI / 2 };
  const RACKS = { pos: V(-19.6, -8.4), face: Math.PI };
  const PRESENTER = { pos: V(21, -8.9), face: 0 };
  const WISH = { pos: V(FOUNT.x, FOUNT.z - FOUNT.r - 0.8), face: 0 };
  const PP = [{ pos: V(TT.x - TT.len / 2 - 0.85, TT.z), face: Math.PI / 2 }, { pos: V(TT.x + TT.len / 2 + 0.85, TT.z), face: -Math.PI / 2 }];
  const FS = [{ pos: V(FB.x - 1.65, FB.z), face: Math.PI / 2 }, { pos: V(FB.x + 1.65, FB.z), face: -Math.PI / 2 }];
  const CHASE = [V(2.5, 13.2), V(2.5, 19.2), V(5.4, 16), V(12.5, 13.4), V(12.8, 18.2), V(18, 13.4), V(18, 18.8), V(24, 13.8), V(24, 18.2)];
  const CHASE_ADJ = [[1, 2, 3], [0, 2, 4], [0, 1, 3], [0, 2, 4, 5], [1, 3, 6], [3, 6, 7], [4, 5, 8], [5, 8], [6, 7]];
  const venue = { pingpong: false, foosball: false, tag: false };
  let lastMeeting = -200, lastAI = -100, aiOn = true;
  const scenes = new Set();

  const facts = () => {
    const c = world.counts || {};
    return { results: c.search_results || 0, fits: c.recommended || 0, scored: c.scored || 0, rejected: c.rejected || 0, top: world.top || '' };
  };
  const fill_ = (text, f) => text.replace(/\{(\w+)\}/g, (_, k) => String(f[k] ?? ''));
  /** A script of this kind that was not heard lately (remembered in this browser), else the one heard longest ago. */
  function pickScript(kind) {
    const pool = KINDS[kind] || BANTER;
    const id = (sc) => sc.lines[0][1];
    const unseen = pool.filter((sc) => !saved.seen.includes(id(sc)));
    const sc = unseen.length ? pick(unseen) : pool.slice().sort((x, y) => saved.seen.indexOf(id(x)) - saved.seen.indexOf(id(y)))[0];
    saved.seen = saved.seen.filter((x) => x !== id(sc)); saved.seen.push(id(sc));
    if (saved.seen.length > 120) saved.seen.shift();
    saveDirty = true;
    return sc;
  }
  const grudgeOf = (a) => (a.grudge && clock < a.grudge.until ? a.grudge.key : null);
  function grudge(a, b, secs = 240) { a.grudge = { key: b.key, until: clock + secs }; const r = rel(a, b); r.fights = (r.fights || 0) + 1; saveDirty = true; }
  const jealousOf = (a) => (a.jealous && clock < a.jealous.until ? a.jealous.key : null);
  function relWord(A, B) {
    if (grudgeOf(A) === B.key || grudgeOf(B) === A.key) return 'they just had a fight and one holds a grudge';
    const r = saved.rel[relKey(A.key, B.key)];
    if (!r) return 'colleagues';
    const games = Object.values(r.wins || {}).reduce((x, y) => x + y, 0);
    if ((r.fights || 0) >= 3) return 'frenemies who bicker a lot';
    if (games >= 3) return 'competitive rivals at games';
    return r.chats >= 4 ? 'close friends' : 'colleagues';
  }
  /** What kind of chat two agents have: their history, their moods and a bit of chance. */
  function dramaFor(A, B) {
    if (runActive) return pick(['break', 'break', 'satire', 'banter']);
    if (grudgeOf(A) === B.key || grudgeOf(B) === A.key) return Math.random() < 0.6 ? 'argument' : 'console';
    if (jealousOf(A) === B.key) return 'jealous';
    if (A.mood.stress > 0.55 || B.mood.stress > 0.55) return Math.random() < 0.55 ? 'argument' : 'satire';
    const x = Math.random();
    return x < 0.24 ? 'banter' : x < 0.48 ? 'satire' : x < 0.68 ? 'argument' : x < 0.79 ? 'jealous' : x < 0.92 ? 'scheme' : 'banter';
  }
  const TOPIC = { argument: 'arguing', scheme: 'plotting something', jealous: 'having a jealous moment', satire: 'roasting job ads',
    console: 'having a heart-to-heart', banter: 'chatting', break: 'chatting on a break' };
  const free = (a) => !a.hasWork && !a.convo && !a.meeting && !a.scene && (!runActive || ['done', 'skipped'].includes(a.state));
  function takeSpotPair(names) {
    for (const n of names.sort(() => Math.random() - 0.5)) { const pr = SPOTS[n]; if (pr.every((s) => !s.busy)) return pr; }
    return null;
  }
  function claim(a, spot) { if (a.spot) a.spot.busy = false; a.spot = spot; if (spot) spot.busy = true; }
  function leaveSeat(a) { return a.seated ? [T.stand()] : []; }
  const moodWord = (a) => (a.mood.energy < 0.25 ? 'tired' : a.mood.joy > 0.75 ? 'cheerful' : a.mood.stress > 0.6 ? 'stressed' : a.mood.joy < 0.3 ? 'a bit down' : 'relaxed');
  const knows = (a) => a.mem.slice(0, 4).map((m) => m.text);

  /** A shared multi-agent activity; cancelling it (work arrived) frees the venue and everyone in it. */
  function newScene(kind, members, extra = {}) {
    const sc = { kind, members, cancelled: false, over: false, ...extra,
      cancel() {
        if (this.cancelled) return; this.cancelled = true; this.over = true;
        scenes.delete(this);
        for (const m of members) { if (m.scene === this) m.scene = null; m.lookTarget = null; m.holder.rotation.x = 0; m.doing = ''; if (m.spot) { m.spot.busy = false; m.spot = null; } }
        if (this.onEnd) this.onEnd();
      },
      end() { if (this.over) return; this.over = true; scenes.delete(this); if (this.onEnd) this.onEnd(); },
    };
    for (const m of members) m.scene = sc;
    scenes.add(sc);
    return sc;
  }
  const leave = (sc) => T.call((a) => { if (a.scene === sc) a.scene = null; a.lookTarget = null; a.doing = ''; });

  /** Two agents meet at a spot and talk, taking turns. Live AI lines when a model is free; scripted ones otherwise. */
  function converse(A, B, pair, scene = '', kind = null) {
    kind = kind || dramaFor(A, B);
    const c = { turn: -1, ready: 0, cancelled: false, lines: null, learned: [], ai: false, kind, end: null };
    A.convo = c; B.convo = c;
    const f = facts();
    // a bit of gossip first when A knows something B does not (scripted talk and conversations from the bank alike)
    const gossip = (lines) => {
      const news = A.mem.find((m) => !B.mem.some((x) => x.text === m.text));
      if (!news || Math.random() >= 0.5 || ['argument', 'scheme'].includes(kind)) return lines;
      c.learned = [news.text];
      return [{ who: 0, text: `Did you hear? ${short(news.text, 70)}`, emotion: 'surprised' },
        { who: 1, text: fresh(GOSSIP_REPLY), emotion: pick(['surprised', 'laugh', 'sneaky']) }, ...lines];
    };
    // scripted fallback (the dialogue bank has nothing for this pair yet)
    const fallback = () => {
      const data = DATA_TALK.filter((d) => d.needs.every((n) => f[n]));
      const sc = data.length && ['banter', 'break'].includes(kind) && Math.random() < (runActive ? 0.4 : 0.2)
        ? { lines: pick(data).lines, end: null } : pickScript(kind);
      c.end = sc.end;
      return gossip(sc.lines.map(([who, text, gesture, expr, action]) => ({ who, text: fill_(text, f), gesture, emotion: exprName(expr), action })));
    };
    // conversations come from the server's dialogue bank (written by AI in batches, no AI call per chat), so most
    // chats can use one; the scripted talk above is the fallback
    const wantAI = talk && aiOn && clock - lastAI > 5 && Math.random() < 0.85;
    if (wantAI) {
      lastAI = clock;
      talk({ a: A.key, b: B.key, scene: scene || `on a break ${pair[0].seat ? 'sitting' : 'standing'} ${WHERE_TEXT[roomOf(pair[0].pos)] || ''}`,
        a_knows: knows(A), b_knows: knows(B), moods: { a: moodWord(A), b: moodWord(B) }, drama: kind, relation: relWord(A, B),
        recent: saved.said.slice(-16), working: runActive })
        .then((r) => {
          if (c.lines || !r || !r.lines || !r.lines.length) return;
          c.learned = r.learned || []; c.lines = gossip(r.lines); c.ai = true;
          for (const ln of c.lines) noteSaid(ln.text);
          const map = { make_up: 'makeup', storm_off: 'storm', sulk: 'sulk', chase: 'chase' };
          const w = r.ending_who === 1 ? 1 : 0;
          c.end = map[r.ending] ? { type: map[r.ending], who: w, chaser: w } : null;
        })
        .catch(() => {});
    }
    // sometimes a third agent sneaks up behind them to listen in
    if (!runActive && Math.random() < 0.22) {
      const C = pick(list.filter((o) => o !== A && o !== B && free(o) && !o.busy));
      if (C) {
        const behind = () => { const d = A.holder.position.clone().sub(B.holder.position); d.y = 0; if (d.lengthSq() < 0.01) d.set(1, 0, 0); return A.holder.position.clone().add(d.normalize().multiplyScalar(1.8)); };
        C.nextIdle = clock + 45;
        C.pushIdle(...leaveSeat(C), T.doing('eavesdropping'), T.face('sneaky', 12), T.wait(rand(2, 4)), T.sneak(behind), T.faceAgent(A),
          T.until(() => c.cancelled || (c.lines && c.turn >= c.lines.length), 45),
          T.call((x) => {
            if (c.cancelled) return;
            x.remember(`Overheard ${A.s.name} and ${B.s.name} ${TOPIC[c.kind] || 'chatting'}`, null, 'social');
            if (Math.random() < 0.3) {          // caught listening
              x.face('scared', 2);
              B.pushIdle(T.faceAgent(x), T.face('furious', 2.5), T.say(fresh(['Were you LISTENING?!', 'Hey! Private conversation!', 'Spy! We have a spy!']), 2.2, 'play'));
              pendingEnds.push({ A: B, B: x, end: { type: 'chase', chaser: 0 }, at: clock + 2.6 });
            } else onSay(x.key, fresh(['Interesting…', 'Ooh, juicy.', 'Wait till the others hear this', 'I heard nothing. Nothing!']), 2.2, 'chat');
          }),
          T.call((x) => { x.doing = ''; x.lookTarget = null; }));
      }
    }
    [A, B].forEach((X, idx) => {
      const other = idx ? A : B, spot = pair[idx];
      claim(X, spot);
      const toOther = Math.atan2(pair[1 - idx].pos.x - spot.pos.x, pair[1 - idx].pos.z - spot.pos.z);
      X.pushIdle(...leaveSeat(X), T.doing('chatting'),
        ...(spot.seat ? T.goSit('chair', spot, spot.face ?? toOther, spot.h) : [T.go(() => spot.pos), T.faceAgent(other)]),
        T.call(() => { c.ready++; }), T.until(() => c.ready >= 2 || c.cancelled, 30));
    });
    // the starter waits a few seconds for live lines, "typing", then falls back to scripted talk
    A.pushIdle(T.call((a) => { if (wantAI && !c.lines) onSay(a.key, '…', 6, 'think'); }), T.until(() => c.lines || c.cancelled || !wantAI, 7),
      T.call(() => { if (!c.lines) c.lines = fallback(); c.turn = 0; }));
    const step = (X, idx) => ({
      update(a, dt) {
        if (c.cancelled || !c.lines) return c.cancelled;
        if (c.turn < 0) return false;
        if (c.turn >= c.lines.length) return true;
        const ln = c.lines[c.turn];
        if (ln.who !== idx) return false;
        if (!ln.shown) {
          ln.shown = true;
          const secs = 2.2 + ln.text.length / 22;
          ln.until = clock + secs;
          onSay(a.key, ln.text, secs, c.ai ? 'ai' : ['argument', 'jealous'].includes(c.kind) && /furious|angry/.test(ln.emotion || '') ? 'play' : 'chat');
          if (ln.emotion) a.face(ln.emotion, secs);
          if (ln.gesture) a.gesture(ln.gesture);
          const o = idx ? A : B;                     // the listener reacts
          if (ln.action) act(a, o, ln.action);
          else if (/angry|furious/.test(ln.emotion || '') && Math.random() < 0.65) o.face(pick(['scared', 'annoyed', 'angry']), 1.8);
          else if (ln.emotion === 'laugh' && Math.random() < 0.6) o.face('laugh', 2);
          else if (ln.emotion === 'sneaky' && Math.random() < 0.5) o.face('sneaky', 2);
          else if (/\?$/.test(ln.text) && !o.seated && Math.random() < 0.4) o.gesture('Yes');
        }
        if (a.awayUntil && !a.seated) {            // turned its back in a huff, then turns round again
          const o = idx ? A : B;
          const to = Math.atan2(o.holder.position.x - a.holder.position.x, o.holder.position.z - a.holder.position.z);
          turnTo(a, clock < a.awayUntil ? to + Math.PI : to, dt * 6);
          if (clock > a.awayUntil + 1.2) a.awayUntil = 0;
        }
        if (clock >= ln.until) c.turn++;
        return false;
      },
    });
    A.pushIdle(step(A, 0));
    B.pushIdle(step(B, 1));
    for (const [X, other] of [[A, B], [B, A]]) {
      X.pushIdle(T.until(() => c.cancelled || (c.lines && c.turn >= c.lines.length), 60), T.wait(rand(1, 3)), T.call((a) => {
        if (!c.cancelled && a === B) {
          for (const t of c.learned || []) if (B.remember(t, A.key, 'heard')) onSay(B.key, `learned from ${A.s.name}: ${short(t, 60)}`, 0.01, 'memory');
          const fight = ['argument', 'jealous'].includes(c.kind);
          if (!fight) bond(A, B);
          A.feel(fight ? -0.03 : 0.06, 0.05, fight ? 0.08 : -0.05); B.feel(fight ? -0.03 : 0.06, 0.05, fight ? 0.08 : -0.05);
          let end = c.end;
          if (end && runActive && !['makeup', 'storm', 'sulk'].includes(end.type)) end = null;    // no chases while others work
          if (end) pendingEnds.push({ A, B, end, at: clock + 0.4 });
        }
        if (c.end) a.nextIdle = Math.max(a.nextIdle, clock + 6);      // keep free for how the chat ends
        a.convo = null; a.lookTarget = null; a.doing = ''; a.awayUntil = 0;
      }));
      void other;
    }
    return c;
  }
  /** A physical beat in a conversation. S acts on L. */
  function act(S, L, action) {
    if (action === 'stomp') S.gesture('Jump');
    else if (action === 'facepalm') { S.gesture('No'); S.face('annoyed', 2.2); }
    else if (action === 'turnaway') S.awayUntil = clock + 2.6;
    else if (action === 'highfive' || action === 'hug') {
      S.gesture('ThumbsUp'); L.gesture(action === 'hug' ? 'Wave' : 'ThumbsUp');
      S.face(action === 'hug' ? 'love' : 'happy', 2.4); L.face('happy', 2.4); bond(S, L);
    } else if (action === 'shove' || action === 'bonk') {
      S.gesture('Punch');
      const d = L.holder.position.clone().sub(S.holder.position); d.y = 0; if (d.lengthSq() < 0.01) d.set(1, 0, 0);
      L.hitAt = clock + 0.3; L.hitKind = action; L.hitDir = d.normalize();
      if (action === 'bonk') { S.remember(`Bonked ${L.s.name}`, null, 'social'); L.remember(`${S.s.name} bonked me!`, null, 'social'); }
    }
  }
  // endings wait until both have finished their chat steps
  const pendingEnds = [];
  const pendingConsole = [];
  function runEnds() {
    for (let i = pendingEnds.length - 1; i >= 0; i--) {
      const p = pendingEnds[i];
      if (clock < p.at) continue;
      const ready = (x) => !x.convo && !x.meeting && !x.hasWork && (!x.scene || x.scene.over);
      if (!ready(p.A) || !ready(p.B)) { if (clock - p.at > 12) pendingEnds.splice(i, 1); continue; }
      pendingEnds.splice(i, 1);
      runEnding(p.A, p.B, p.end);
    }
    for (let i = pendingConsole.length - 1; i >= 0; i--) {
      const p = pendingConsole[i];
      if (clock < p.at) continue;
      pendingConsole.splice(i, 1);
      const S = p.S;
      if (!['sulking', 'storming off'].includes(S.doing) || S.hasWork) continue;
      const fr = friendsOf(S).best;
      const F = (fr && free(agents[fr.key]) && !agents[fr.key].busy && grudgeOf(S) !== fr.key && agents[fr.key])
        || pick(list.filter((o) => o !== S && free(o) && !o.busy && grudgeOf(S) !== o.key));
      if (!F) continue;
      S.queue = S.queue.filter((t) => !t.idle); if (S.task && S.task.idle) S.task = null;
      if (S.spot) { S.spot.busy = false; S.spot = null; }
      const here = S.holder.position.clone();
      const side = F.holder.position.clone().sub(here); side.y = 0; if (side.lengthSq() < 0.01) side.set(1, 0, 0);
      converse(F, S, [{ pos: here.clone().add(side.normalize().multiplyScalar(1.4)) }, { pos: here }], `${S.s.name} is upset and sulking; ${F.s.name} comes to cheer it up`, 'console');
    }
  }
  function runEnding(A, B, end) {
    const P = [A, B];
    const who = P[end.who === 1 ? 1 : 0], other = who === A ? B : A;
    if (end.type === 'makeup') { for (const X of P) { X.face('happy', 2.5); X.feel(0.08, 0, -0.08); X.grudge = null; } bond(A, B, 2); }
    else if (end.type === 'storm') storm(who, other);
    else if (end.type === 'sulk') sulk(who, other);
    else if (end.type === 'chase') { const C = P[end.chaser === 1 ? 1 : 0], R = C === A ? B : A; if (!chase(C, R)) storm(R, C); }
    else if (end.type === 'sneak') sneakSnack(who, other);
    else if (end.type === 'escape') escapeTogether(A, B);
  }
  function storm(S, from) {
    grudge(S, from);
    const spot = pick([...SPOTS.window, ...SPOTS.garden, ...SPOTS.gameNook, ...SPOTS.lounge].filter((x) => !x.busy));
    if (!spot) return;
    claim(S, spot);
    S.nextIdle = clock + 30;
    S.pushIdle(...leaveSeat(S), T.doing('storming off'), T.face('furious', 3),
      T.say(fresh(['Whatever!', 'I am DONE talking to you.', 'Do not follow me.', 'Ugh!', 'This conversation is over.']), 2.2, 'play'),
      T.go(() => spot.pos, true), T.faceAngle(rand(-Math.PI, Math.PI)), T.doing('sulking'), T.face('angry', 6), T.wait(rand(2, 4)),
      T.say(fresh(MUTTER), 2.6, 'chat'), T.face('sad', 6), T.wait(rand(5, 9)), T.call((a) => { a.doing = ''; a.feel(0.05, 0, -0.1); }));
    from.pushIdle(T.face(pick(['annoyed', 'surprised', 'sad']), 2.5), T.say(fresh(['Fine, go!', '…was it something I said?', 'Drama queen.', 'Okay… that escalated.']), 2.4, 'chat'));
    S.remember(`Stormed off after a fight with ${from.s.name}`, null, 'social'); from.remember(`${S.s.name} stormed off in a huff`, null, 'social');
    if (Math.random() < 0.6) pendingConsole.push({ S, at: clock + rand(8, 12) });
  }
  function sulk(S, from) {
    grudge(S, from, 150);
    const seat = pick([...SPOTS.bench, ...SPOTS.bags].filter((x) => !x.busy));
    if (!seat) { storm(S, from); return; }
    claim(S, seat);
    S.nextIdle = clock + 30;
    S.pushIdle(...leaveSeat(S), T.doing('sulking'), T.face('sad', 4), ...T.goSit('sofa', seat), T.face('sad', 9),
      T.say(fresh(MUTTER), 2.6, 'chat'), T.wait(rand(9, 14)), T.call((a) => { a.doing = ''; }), T.stand());
    if (Math.random() < 0.7) pendingConsole.push({ S, at: clock + rand(7, 11) });
  }
  /** C chases R: R runs off through the doors; C follows R's footsteps. Caught → a cartoon bonk. */
  function chase(C, R) {
    if (venue.chase || C.busy || R.busy) return false;
    venue.chase = true;
    const sc = newScene('chase', [C, R], { caught: false, trail: [], onEnd() { venue.chase = false; } });
    grudge(C, R, 180);
    const far = [V(2.5, 16), V(18, 16), V(-8.5, 15.5), V(23.5, 7.4), V(-20, 8.5), V(5.5, -9.2), V(-19.6, -6.5), V(24, 18)];
    const cp = C.holder.position.clone();
    const goal = far.sort((x, y) => y.distanceTo(cp) - x.distanceTo(cp))[Math.floor(Math.random() * 3)];
    R.pushIdle(...leaveSeat(R), T.doing('running away'), T.face('scared', 3), T.say(fresh(ESCAPE_SHOUT), 1.8, 'play'), T.go(() => goal, true),
      T.call((a) => { if (!sc.caught && !sc.over) { a.face('laugh', 3); onSay(a.key, fresh(['Ha! Lost you!', 'Safe!', 'Hiding here forever now', 'Is it gone?']), 2, 'play'); } }),
      T.until(() => sc.over, 16), leave(sc));
    C.pushIdle(...leaveSeat(C), T.doing('chasing'), T.wait(0.5), T.face('furious', 5), T.say(fresh(CHASE_SHOUT), 1.8, 'play'),
      T.go(() => sc.trail.length ? sc.trail[0].clone() : R.holder.position.clone(), true),
      { start(a) { a.play('Running', 0.2); this.t = 0; }, update(a, dt) {
        if (sc.over) return true;
        this.t += dt;
        const pos = a.holder.position, rp = R.holder.position;
        let tgt = rp;
        if (pos.distanceTo(rp) > 1.6 && sc.trail.length) { tgt = sc.trail[0]; if (pos.distanceTo(tgt) < 0.45) { sc.trail.shift(); return false; } }
        const dx = tgt.x - pos.x, dz = tgt.z - pos.z, d = Math.hypot(dx, dz) || 1, st = 6.1 * speed * dt;
        pos.x += dx / d * st; pos.z += dz / d * st; turnTo(a, Math.atan2(dx, dz), dt * 12);
        if (pos.distanceTo(rp) < 1.0) { sc.caught = true; return true; }
        return this.t > 12;
      } },
      T.call((a) => {
        if (sc.over) return;
        if (sc.caught) {
          a.play('Idle', 0.2); a.lookTarget = () => R.holder.position;
          R.queue = R.queue.filter((t) => !t.idle); if (R.task && R.task.idle) R.task = null;
          act(a, R, 'bonk'); onSay(a.key, fresh(['GOTCHA!', 'Got you now!', 'Justice!', 'BONK.']), 2, 'play');
          R.pushIdle(T.wait(3), T.say(fresh(['Owww!', 'Okay okay, I am sorry!', 'Not the antenna!', 'I surrender!']), 2.4, 'play'), T.face('sad', 3), leave(sc));
          a.remember(`Caught ${R.s.name} and gave it a bonk`, null, 'social'); R.remember(`${a.s.name} chased me down and bonked me`, null, 'social');
          a.feel(0.12, -0.15, -0.15); R.feel(-0.05, -0.15, 0.05);
        } else {
          a.play('Idle', 0.3); a.face('tired', 3);
          onSay(a.key, fresh(['Come back… here…', 'You got lucky this time', 'I know where your desk is!', 'Too… tired…']), 2.6, 'play');
          a.feel(-0.03, -0.2, 0.05); R.remember(`Escaped from ${a.s.name}`, null, 'social');
        }
      }),
      T.wait(2.6), T.call(() => sc.end()), leave(sc));
    sc.tick = () => { if (!sc.trailT || clock - sc.trailT > 0.12) { sc.trail.push(R.holder.position.clone()); sc.trailT = clock; if (sc.trail.length > 140) sc.trail.shift(); } };
    focus = R.holder.position; focusUntil = clock + 8;
    return true;
  }
  /** S tiptoes to the pantry for someone's snack; a lookout may help; the owner may notice — then it is a chase. */
  function sneakSnack(S, look = null) {
    if (COFFEE.busy || S.busy) return false;
    claim(S, COFFEE);
    S.nextIdle = clock + 40;
    const owner = pick(list.filter((o) => o !== S && o !== look && free(o) && !o.busy && !o.scene));
    const seen = owner && Math.random() < 0.6;
    if (look && !look.busy) {
      const post = SPOTS.cooler[0];
      look.pushIdle(...leaveSeat(look), T.doing('keeping watch'), T.face('sneaky', 12), T.sneak(() => post.pos), T.faceAngle(Math.PI / 2),
        T.say(fresh(['Coast is clear…', 'Go, go, go!', 'I see nothing. I am a plant.']), 2.2, 'chat'), T.wait(4),
        ...(seen ? [T.face('scared', 2), T.say(fresh(['ABORT! ABORT!', 'We are SPOTTED!', 'Every robot for itself!']), 2, 'play'), T.go(() => SPOTS.garden[0].pos, true)] : [T.wait(3)]),
        T.call((a) => { a.doing = ''; }));
    }
    S.pushIdle(...leaveSeat(S), T.doing('sneaking to the pantry'), T.face('sneaky', 14), T.sneak(() => COFFEE.pos), T.faceAngle(COFFEE.face),
      T.say(fresh(['Shh…', 'Nobody saw anything…', 'Just one bite…', 'Smells like Bawarchi…']), 2.2, 'chat'), T.wait(1.6),
      T.call((a) => { a.face('love', 2); }), T.anim('Yes'),
      T.call((a) => {
        claim(a, null);
        if (seen && free(owner) && !owner.busy) {
          owner.pushIdle(T.faceAgent(a), T.face('furious', 3), T.say(fresh(['HEY! That is MY biryani!', 'Put. It. Down.', 'I SAW THAT!']), 2.2, 'play'));
          a.face('scared', 2);
          a.remember(`Got caught stealing ${owner.s.name}'s snack`, null, 'social');
          pendingEnds.push({ A: owner, B: a, end: { type: 'chase', chaser: 0 }, at: clock + 2.4 });
        } else {
          a.pushIdle(T.face('proud', 3), T.say(fresh(['Mission accomplished.', 'Perfect crime.', 'Delicious. No regrets.']), 2.4, 'chat'), T.go(() => a.home), T.call((x) => { x.doing = ''; }));
          a.remember('Stole a snack from the pantry and got away with it', null, 'social');
        }
      }));
    return true;
  }
  function escapeTogether(A, B) {
    const pair = takeSpotPair(['garden', 'gameNook', 'lounge']);
    if (!pair) return;
    [A, B].forEach((X, i) => {
      claim(X, pair[i]);
      X.pushIdle(...leaveSeat(X), T.doing('hiding from meetings'), T.face('sneaky', 10), T.sneak(() => pair[i].pos), T.faceAgent(i ? A : B), T.face('laugh', 3),
        ...(i === 0 ? [T.say(fresh(['We made it…', 'Nobody followed us, right?', 'Freedom!']), 2.4, 'chat')]
          : [T.wait(2.6), T.say(fresh(['Shh! Not so loud!', 'If anyone asks, I was never here', 'Best. Plan. Ever.']), 2.4, 'chat')]),
        T.wait(rand(4, 7)), T.call((a) => { a.doing = ''; a.lookTarget = null; }));
    });
    bond(A, B, 2);
  }
  /** Someone the agent is jealous of: it watches from a distance, mutters, and sometimes goes to have it out. */
  function jealousWatch(A) {
    const B = agents[jealousOf(A)];
    if (!B || A.busy) return false;
    A.jealous = null;
    const spot = () => { const d = A.holder.position.clone().sub(B.holder.position); d.y = 0; if (d.lengthSq() < 0.01) d.set(1, 0, 0); return B.holder.position.clone().add(d.normalize().multiplyScalar(3.4)); };
    A.pushIdle(...leaveSeat(A), T.doing('watching someone jealously'), T.face('jealous', 10), T.go(spot), T.faceAgent(B), T.wait(rand(1.5, 3)),
      T.say(() => fresh(JEALOUS_MUTTER).replace('{name}', `the ${B.s.name}`), 2.8, 'chat'), T.wait(rand(1.5, 3)),
      T.call((a) => {
        a.doing = ''; a.lookTarget = null;
        const pair = free(B) && !B.busy && !B.convo && Math.random() < 0.55 ? takeSpotPair(['floorA', 'floorB', 'lounge', 'garden', 'gameNook']) : null;
        if (pair) converse(a, B, pair, `${a.s.name} is jealous of ${B.s.name} and confronts it`, 'jealous');
        else a.face('sad', 3);
      }));
    return true;
  }
  /** A play fight: shoves, the odd knock-down, then a truce (or not). */
  function playFight(A, B) {
    const pair = takeSpotPair(['lounge', 'floorA', 'floorB', 'garden']);
    if (!pair) return false;
    const sc = newScene('fight', [A, B], { ready: 0, hits: 0, n: 4 + Math.floor(Math.random() * 4), t: 0 });
    [A, B].forEach((X, i) => {
      claim(X, pair[i]);
      X.pushIdle(...leaveSeat(X), T.doing('in a play fight'), T.go(() => pair[i].pos), T.faceAgent(i ? A : B), T.call(() => { sc.ready++; }),
        T.until(() => sc.ready >= 2 || sc.over, 30), T.until(() => sc.over, 45), leave(sc));
    });
    sc.tick = (dt) => {
      if (sc.ready < 2 || sc.over) return;
      for (const [X, i] of [[A, 0], [B, 1]]) if (!X.stunUntil && !X.knock) X.holder.position.lerp(pair[i].pos, Math.min(1, dt * 1.5));
      if (!sc.started) { sc.started = true; onSay(A.key, fresh(['Bring it on!', 'En garde!', 'You asked for this!']), 2, 'play'); A.face('furious', 2); B.face('scared', 2); sc.t = 1.3; return; }
      sc.t -= dt; if (sc.t > 0) return;
      const H = sc.hits % 2 ? B : A, L = H === A ? B : A;
      if (L.stunUntil) { sc.t = 0.5; return; }
      act(H, L, Math.random() < 0.25 ? 'bonk' : 'shove');
      H.face(pick(['laugh', 'furious', 'proud']), 1.2);
      if (Math.random() < 0.5) onSay(H.key, fresh(['Take that!', 'Hiyaa!', 'Pow!', 'Not the face screen!', 'Ha!', 'Too slow!']), 1.4, 'play');
      sc.hits++; sc.t = rand(1.1, 1.8);
      if (sc.hits >= sc.n) {
        sc.end();
        const W = pick([A, B]), Lo = W === A ? B : A;
        if (Math.random() < 0.7) {
          W.pushIdle(T.wait(1.2), T.face('laugh', 3), T.say(fresh(['Truce! Truce!', 'Okay, okay — you win', 'Same time tomorrow?']), 2.4, 'play'));
          Lo.pushIdle(T.wait(2.4), T.face('laugh', 3), T.anim('ThumbsUp'));
          bond(A, B, 2);
        } else {
          W.pushIdle(T.wait(1), T.face('proud', 3), T.say(fresh(['Undefeated!', 'Bow before me.', 'Too easy.']), 2.4, 'play'), T.loop('Dance', 2));
          pendingEnds.push({ A: Lo, B: W, end: { type: 'storm', who: 0 }, at: clock + 3.5 });
        }
        A.remember(`Had a play fight with ${B.s.name}`, null, 'social'); B.remember(`Had a play fight with ${A.s.name}`, null, 'social');
      }
    };
    return true;
  }
  const WHERE_TEXT = { work: 'on the work floor', pantry: 'in the pantry', server: 'in the server room', meet: 'in the meeting room', hall: 'in the hallway', game: 'in the game room', garden: 'in the garden' };

  function coffeeBreak(A) {
    if (COFFEE.busy) { wander(A); return; }
    claim(A, COFFEE);
    A.pushIdle(...leaveSeat(A), T.doing('making chai'), T.go(() => COFFEE.pos), T.faceAngle(COFFEE.face),
      T.call(() => { brewing = 4; }), T.say(fresh(['Chai time', 'One cutting chai, please', 'Filter coffee today', 'Refuelling…', 'Extra ginger. Trust me.']), 2.6, 'chat'),
      T.wait(3.2), T.call((a) => { a.feel(0.05, 0.35, -0.1); a.face('love', 2); }), T.anim('Yes'));
    const seat = pick([...SPOTS.pantryTable, ...SPOTS.sofa].filter((s) => !s.busy));
    if (seat) { claim(A, seat); A.pushIdle(T.doing('sipping chai'), ...T.goSit(SPOTS.sofa.includes(seat) ? 'sofa' : 'chair', seat), T.wait(rand(4, 9))); }
  }
  function wander(A) {
    const choice = pick(['window', 'desk', 'racks', 'lounge', 'garden']);
    claim(A, null);
    if (choice === 'desk') { A.pushIdle(...leaveSeat(A), T.doing('tidying its desk'), ...T.goSit('desk', A.deskSeat(), A.faceAngle), T.wait(rand(3, 7))); return; }
    if (choice === 'racks') { A.pushIdle(...leaveSeat(A), T.doing('checking the servers'), T.go(() => RACKS.pos), T.faceAngle(RACKS.face), T.call(() => { serverBusy = 1.2; }), T.anim('Yes')); return; }
    const spot = pick(SPOTS[choice === 'window' ? 'window' : choice === 'garden' ? 'garden' : 'lounge'].filter((s) => !s.busy));
    if (!spot) return;
    claim(A, spot);
    A.pushIdle(...leaveSeat(A), T.doing(choice === 'window' ? 'looking out of the window' : choice === 'garden' ? 'strolling in the garden' : 'relaxing in the lounge'),
      T.go(() => spot.pos), T.faceAngle(choice === 'window' ? Math.PI : rand(-1, 1)), T.wait(rand(2, 5)),
      ...(Math.random() < 0.4 ? [T.say(fresh(['Nice view', 'Peaceful…', 'I should do this more often', 'Thinking about embeddings', 'Is it lunch yet?']), 2.4, 'chat')] : []));
  }
  function nap(A) {
    const spot = pick([...SPOTS.sofa, ...SPOTS.bags, ...SPOTS.bench].filter((s) => !s.busy));
    if (!spot) { coffeeBreak(A); return; }
    claim(A, spot);
    const until = { t: 0 };
    A.pushIdle(...leaveSeat(A), T.doing('walking to a nap'), ...T.goSit('sofa', spot), T.doing('napping'),
      T.call((a) => { until.t = clock + rand(14, 24); onSay(a.key, fresh(['Five minutes. Just five.', 'Do not wake me unless it is biryani', 'Power nap…']), 2.6, 'chat'); }),
      { update(a, dt) { a.feel(0, dt * 0.03, -dt * 0.01); if (Math.random() < dt * 0.35) onSay(a.key, 'z z z', 1.6, 'think'); return clock > until.t || a.doing !== 'napping'; } },
      T.call((a) => { if (a.doing === 'napping') { a.doing = ''; a.face('happy', 2); } }), T.stand());
    // sometimes a friend sneaks up with a prank
    const P2 = list.filter((o) => o !== A && free(o) && !o.busy);
    if (P2.length && Math.random() < 0.45) {
      const Pk = pick(P2);
      const near = spot.pos.clone().add(V(0.9, 0.6));
      Pk.pushIdle(...leaveSeat(Pk), T.doing('up to no good'), T.wait(rand(6, 10)), T.go(() => near), T.faceAgent(A), T.face('wink', 2),
        T.until(() => A.doing === 'napping', 12),
        T.call((p) => {
          if (A.doing !== 'napping') return;
          onSay(p.key, fresh(['BOO!', 'WAKE UP! The Verifier found a fake job!', 'Surprise standup!']), 2.2, 'play');
          A.doing = ''; A.face('scared', 2.2);
          A.queue = A.queue.filter((t) => !t.idle); A.task = null;
          A.pushIdle(T.stand(), T.anim('Jump'), T.say(fresh(['AAAH!', 'WHAT?! WHO?!', 'My heart! …I do not have one.']), 2.2, 'play'), T.face('angry', 2.5), T.wait(1.2),
            T.say(fresh(['Not funny.', 'I will get you back for this', '…okay, that was a bit funny']), 2.6, 'chat'), T.face('laugh', 2));
          p.remember(`Pranked ${A.s.name} during a nap`, null, 'social'); A.remember(`${p.s.name} pranked me during my nap!`, null, 'social');
          bond(p, A); p.feel(0.15, 0, 0); A.feel(-0.05, 0.1, 0.05);
        }),
        T.face('laugh', 3), T.anim('Yes'), T.say(fresh(['Got you!', 'Hahaha, your FACE!', 'Worth it.', 'Ten out of ten prank.']), 2.4, 'play'), T.call((p) => { p.doing = ''; p.lookTarget = null; }));
      Pk.nextIdle = clock + 40;
    }
  }
  function soloDance(A) {
    const spot = pick([V(4, 14.8), V(16.5, 17.5), V(-2.5, 6.5), V(-12, 18.2)]);
    A.pushIdle(...leaveSeat(A), T.doing('dancing'), T.go(() => spot), T.face('happy', 7), T.say(fresh(['This song though!', 'Nobody is watching, right?', 'Robot dance, activated', 'Naatu naatu!']), 2.6, 'play'),
      T.call((a) => { a.danceUntil = clock + 6; }), T.loop('Dance', 6), T.call((a) => { a.feel(0.15, -0.05, -0.1); a.doing = ''; }));
  }
  function arcade(A) {
    const m = arcades.find((x) => !x.busy); if (!m) { wander(A); return; }
    m.busy = true;
    const sc = newScene('arcade', [A], { onEnd() { m.busy = false; m.play = 0; } });
    A.pushIdle(...leaveSeat(A), T.doing('playing the arcade'), T.go(() => m.spot.pos), T.faceAngle(m.spot.face), T.face('focused', 9),
      T.call(() => { m.play = 1; m.score = 0; }),
      { start() { this.t = rand(6, 10); }, update(a, dt) { if (sc.over) return true; this.t -= dt; m.score += dt * rand(40, 140); a.holder.rotation.y = m.spot.face + Math.sin(clock * 26) * 0.05; return this.t <= 0; } },
      T.call((a) => {
        if (sc.over) return;
        const win = Math.random() < 0.45;
        a.face(win ? 'proud' : 'sad', 3); onSay(a.key, win ? `NEW HIGH SCORE! ${Math.round(m.score)}` : fresh(['Game over… again', 'That ghost cheated', 'One more coin. Just one.']), 2.8, 'play');
        if (win) { a.gesture('Jump'); a.remember(`Set a new arcade high score (${Math.round(m.score)})`, null, 'social'); a.feel(0.2, -0.05, -0.05); } else { a.gesture('No'); a.feel(-0.05, -0.05, 0.05); }
        m.play = 0;
      }), T.wait(2), T.call(() => sc.end()), leave(sc));
  }
  function swingRide(A) {
    if (swingSpot.busy) { wander(A); return; }
    claim(A, swingSpot);
    const sc = newScene('swing', [A], { onEnd() { swingAmp = 0; A.holder.rotation.x = 0; } });
    A.pushIdle(...leaveSeat(A), T.doing('on the swing'), T.go(() => V(SW.x, SW.z + SIT_FWD + 0.4)), T.sit('swing', V(SW.x, SW.z), 0, 0.475),
      T.call((a) => { a.riding = true; swingAmp = 0.42; onSay(a.key, fresh(['Wheee!', 'Higher!', 'This is the best part of the job']), 2.4, 'play'); a.face('laugh', 3); }),
      { start() { this.t = rand(8, 13); }, update(a, dt) { this.t -= dt; a.feel(0, 0, -dt * 0.01); if (this.t < 2) swingAmp *= 0.97; return this.t <= 0 || sc.over; } },
      T.call((a) => { a.riding = false; a.holder.rotation.x = 0; a.holder.position.set(SW.x, 0, SW.z + 0.15); a.feel(0.15, 0, -0.1); sc.end(); }), T.stand(), leave(sc));
  }
  function wish(A) {
    if (WISH.busy) { wander(A); return; }
    claim(A, WISH);
    A.pushIdle(...leaveSeat(A), T.doing('making a wish'), T.go(() => WISH.pos), T.faceAngle(WISH.face), T.face('love', 4),
      T.say(fresh(['A job post with 3 applicants, please', 'One referral, universe. Just one.', 'May every posting be fresh', 'Let the next match be a 95']), 3, 'chat'),
      T.call((a) => { const from = worldPos(a.holder).setY(1.5); flying.push({ p: (() => { const c = cyl(0.06, 0.06, 0.015, P(0xf2c14e, { metalness: 0.9, roughness: 0.2 }), 12); scene.add(c); return c; })(), from, to: V(FOUNT.x + rand(-0.5, 0.5), FOUNT.z + rand(-0.4, 0.4), 0.47), t: 0, d: 0.8, onLand: () => { const r = ripples.find((x) => x.t >= 1) || ripples[0]; r.t = 0; r.r.position.set(FOUNT.x, 0.47, FOUNT.z); } }); }),
      T.anim('Yes'), T.wait(1.5), T.call((a) => { a.feel(0.1, 0, -0.05); }));
  }

  /** Ping-pong or foosball: first to 5 (foosball 3). The winner and the score go into both agents' memories. */
  function duel(kind, A, B) {
    if (venue[kind]) return false;
    venue[kind] = true;
    const spots = kind === 'pingpong' ? PP : FS;
    const goal = kind === 'pingpong' ? 5 : 3;
    const label = kind === 'pingpong' ? 'ping-pong' : 'foosball';
    const sc = newScene(kind, [A, B], { score: [0, 0], ready: 0, onEnd() { venue[kind] = false; ball.visible = false; for (const p of [A, B]) if (p.paddle) { p.paddle.parent.remove(p.paddle); p.paddle = null; } } });
    const sideOf = (X) => (X === A ? 0 : 1);
    [A, B].forEach((X, i) => {
      claim(X, spots[i]);
      X.pushIdle(...leaveSeat(X), T.doing(`playing ${label}`), T.go(() => spots[i].pos), T.faceAngle(spots[i].face),
        T.call((a) => {
          a.lookTarget = () => (kind === 'pingpong' ? ball.position : fball.position);
          if (kind === 'pingpong' && a.rig.hand) { const pd = new THREE.Group(); const blade = cyl(0.17, 0.17, 0.03, paddleM, 18); blade.rotation.x = Math.PI / 2; pd.add(blade); const hd = cyl(0.03, 0.03, 0.16, darkWood, 6); hd.position.y = -0.2; pd.add(hd); const ws = a.rig.hand.getWorldScale(new THREE.Vector3()); pd.scale.setScalar(1 / ws.x); a.rig.hand.add(pd); a.paddle = pd; }
          sc.ready++;
        }),
        T.until(() => sc.ready >= 2 || sc.over, 40),
        T.until(() => sc.over, 160),
        leave(sc));
    });
    // the rally runs from the scene update (see sceneTick) and ends the game
    sc.rally = { from: 0, t: 0, d: 0.75, hits: 0, len: 2 + Math.floor(Math.random() * 6), started: false, pause: 1.2 };
    sc.tick = (dt) => {
      if (sc.ready < 2 || sc.over) return;
      const r = sc.rally;
      if (!r.started) { r.started = true; onSay(A.key, fresh(['Serve!', 'Ready?', 'Prepare to lose']), 2, 'play'); B.face('focused', 3); }
      if (r.pause > 0) { r.pause -= dt; ball.visible = kind === 'pingpong'; return; }
      const hitter = r.from ? B : A, recv = r.from ? A : B;
      const p0 = hitter.holder.position, p1 = recv.holder.position;
      r.t += dt * speed / r.d;
      const u = Math.min(1, r.t);
      if (kind === 'pingpong') {
        ball.visible = true;
        const x0 = p0.x + Math.sign(TT.x - p0.x) * 0.6, x1 = p1.x + Math.sign(TT.x - p1.x) * 0.6;
        const z0 = r.z0 ?? TT.z, z1 = r.z1 ?? TT.z + rand(-0.8, 0.8);
        r.z0 = z0; r.z1 = z1;
        ball.position.set(x0 + (x1 - x0) * u, 0, z0 + (z1 - z0) * u);
        const tbl = TT.h + 0.07;          // over the net, a bounce on the far half, up to the next paddle
        ball.position.y = u < 0.55 ? 1.3 + (tbl - 1.3) * (u / 0.55) + Math.sin(u / 0.55 * Math.PI) * 0.3 : tbl + Math.sin((u - 0.55) / 0.45 * Math.PI / 2) * 0.35;
        recv.holder.position.z += (clamp(z1, TT.z - 0.9, TT.z + 0.9) - recv.holder.position.z) * Math.min(1, dt * 3);
      } else {
        const x0 = FB.x + (r.from ? 1 : -1) * 0.95, x1 = FB.x + (r.from ? -1 : 1) * 0.95;
        const z0 = r.z0 ?? FB.z, z1 = r.z1 ?? FB.z + rand(-0.4, 0.4); r.z0 = z0; r.z1 = z1;
        fball.position.set(x0 + (x1 - x0) * u, 1.26, z0 + (z1 - z0) * u + Math.sin(u * Math.PI * 3) * 0.12);
        rods.forEach((rd, i) => { rd.rotation.z = Math.sin(clock * 9 + i) * (0.6 + Math.random() * 0.2); });
        for (const p of [A, B]) p.holder.rotation.y = spots[sideOf(p)].face + Math.sin(clock * 18 + sideOf(p)) * 0.08;
      }
      if (u >= 1) {
        r.hits++;
        if (r.hits >= r.len) {                          // the receiver misses: a point for the hitter
          const s = sideOf(hitter); sc.score[s]++;
          recv.face(pick(['surprised', 'angry']), 1.6); hitter.face(pick(['happy', 'proud', 'laugh']), 1.6);
          if (kind === 'pingpong') { ball.position.y = 0.07; }
          const [a, b] = sc.score;
          if (Math.max(a, b) >= goal) { finishDuel(); return; }
          if (Math.random() < 0.55) onSay(hitter.key, fresh([`${Math.max(a, b)}–${Math.min(a, b)}`, 'Ha!', 'Point!', 'Too fast for you', 'Did you even see that?', 'Textbook.', 'Spin shot!', 'Keep up!', 'Again? Sure.']), 1.6, 'play');
          else if (Math.random() < 0.5) onSay(recv.key, fresh(['Nooo!', 'The sun was in my eyes', 'Rematch!', 'Hey!', 'Lucky shot!', 'That was OUT!', 'My paddle is broken', 'I was warming up', 'Net! That was net!']), 1.6, 'play');
          r.len = 2 + Math.floor(Math.random() * 6); r.hits = 0; r.pause = 1.1; r.from = 1 - s; r.z0 = r.z1 = undefined;
        } else {
          r.from = 1 - r.from; r.t = 0; r.z0 = r.z1; r.z1 = undefined;
          if (kind === 'pingpong') recv.swingT = 0;
        }
        r.t = 0;
      }
      // a quick body twist for the swing
      for (const p of [A, B]) if (p.swingT !== undefined && p.swingT < 0.35 && kind === 'pingpong') { p.swingT += dt; p.holder.rotation.y = spots[sideOf(p)].face + Math.sin(p.swingT / 0.35 * Math.PI) * 0.55; }
    };
    function finishDuel() {
      const [a, b] = sc.score;
      const W = a > b ? A : B, L = W === A ? B : A, ws = Math.max(a, b), ls = Math.min(a, b);
      const r = rel(W, L); r.wins[W.key] = (r.wins[W.key] || 0) + 1; bond(W, L); saveDirty = true;
      W.remember(`Beat ${L.s.name} at ${label} ${ws}–${ls}`, null, 'social'); L.remember(`Lost to ${W.s.name} at ${label} ${ls}–${ws} (rematch!)`, null, 'social');
      W.feel(0.2, -0.1, -0.1); L.feel(-0.08, -0.1, 0.05);
      if (Math.random() < 0.6) L.jealous = { key: W.key, until: clock + 300 };
      ball.visible = false;
      sc.end();
      for (const p of [W, L]) if (p.paddle) { p.paddle.parent.remove(p.paddle); p.paddle = null; }
      W.pushIdle(T.face('proud', 3), T.anim('Jump'), T.say(fresh([`${ws}–${ls}! Champion!`, `Too easy. ${ws}–${ls}`, `And THAT is how it is done`]), 2.8, 'play'), T.loop('Dance', 2.5), leave(sc));
      L.pushIdle(T.face('angry', 2.5), T.anim('No'), T.say(fresh(['Best of three?', 'Rematch. Tomorrow. Same time.', 'I let you win. Obviously.']), 2.8, 'play'), T.face('laugh', 2), leave(sc));
      // sometimes they talk about it (live AI when a model is free)
      if (Math.random() < 0.5) {
        const pair = takeSpotPair(['gameNook', 'garden']);
        if (pair) setTimeout(() => { if (!disposed && free(W) && free(L) && !W.busy && !L.busy) converse(W, L, pair, `just finished ${label}; ${W.s.name} won ${ws}–${ls}`); }, 6000);
      }
    }
    return true;
  }

  /** Tag in the garden: the chaser follows the runner's footsteps; caught → a playful bop and a comic fall. */
  function tag(A, B) {
    if (venue.tag) return false;
    venue.tag = true;
    const startR = 3 + Math.floor(Math.random() * 6), startC = startR > 4 ? 0 : 8;
    const sc = newScene('tag', [A, B], { ready: 0, trail: [], node: startR, caught: false, onEnd() { venue.tag = false; } });
    const R = B, C = A;   // A chases
    R.pushIdle(...leaveSeat(R), T.doing('playing tag'), T.go(() => CHASE[startR]), T.call(() => { sc.ready++; }), T.until(() => sc.ready >= 2 || sc.over, 40),
      T.say(fresh(['Catch me if you can!', 'You will never catch me!', 'Too slow!']), 2, 'play'), T.face('laugh', 3),
      { start(a) { a.play('Running', 0.2); this.t = 0; }, update(a, dt) {
        if (sc.over || sc.caught) return true;
        this.t += dt;
        const tgt = CHASE[sc.node], pos = a.holder.position;
        const dx = tgt.x - pos.x, dz = tgt.z - pos.z, d = Math.hypot(dx, dz), st = 5.4 * speed * dt;
        if (d < 0.3) {
          const cp = C.holder.position;
          const opts = CHASE_ADJ[sc.node].map((i) => [i, CHASE[i].distanceTo(cp) + rand(0, 2)]).sort((x, y) => y[1] - x[1]);
          sc.node = opts[0][0];
        } else { pos.x += dx / d * st; pos.z += dz / d * st; turnTo(a, Math.atan2(dx, dz), dt * 12); }
        if (!sc.trailT || clock - sc.trailT > 0.12) { sc.trail.push(pos.clone()); sc.trailT = clock; if (sc.trail.length > 60) sc.trail.shift(); }
        if (this.t > 22) { sc.caught = 'timeout'; return true; }
        return false;
      } },
      { start(a) {
        if (sc.over) return;
        if (sc.caught === 'timeout') { a.play('Idle', 0.3); onSay(a.key, 'Ha! Untouchable!', 2.2, 'play'); a.face('proud', 3); return; }
        a.play('Death', 0.15); a.face('dizzy', 3.5); this.t = 0;
      }, update(a, dt) { this.t = (this.t || 0) + dt; return sc.over || sc.caught === 'timeout' || this.t > 2.6; } },
      T.call((a) => { if (sc.caught === true) { a.play('Idle', 0.9); onSay(a.key, fresh(['Not fair, you have longer legs!', 'I tripped! That does not count!', 'Okay okay, you win']), 2.6, 'play'); } }),
      T.wait(1), T.face('laugh', 2.5), T.call(() => sc.end()), leave(sc));
    C.pushIdle(...leaveSeat(C), T.doing('playing tag'), T.go(() => CHASE[startC]), T.call(() => { sc.ready++; }), T.until(() => sc.ready >= 2 || sc.over, 40),
      T.wait(0.8), T.say(fresh(["You're it! …wait, I'm it. RUN!", 'Here I come!', 'Ready or not!']), 2, 'play'), T.face('happy', 3),
      { start(a) { a.play('Running', 0.2); this.t = 0; }, update(a, dt) {
        if (sc.over || sc.caught) return true;
        this.t += dt;
        const pos = a.holder.position, rp = R.holder.position;
        let tgt = rp;
        if (pos.distanceTo(rp) > 2.2 && sc.trail.length) { tgt = sc.trail[0]; if (pos.distanceTo(tgt) < 0.4) sc.trail.shift(); }
        const dx = tgt.x - pos.x, dz = tgt.z - pos.z, d = Math.hypot(dx, dz) || 1, st = 6.2 * speed * dt;
        pos.x += dx / d * st; pos.z += dz / d * st; turnTo(a, Math.atan2(dx, dz), dt * 12);
        if (pos.distanceTo(rp) < 0.95) { sc.caught = true; return true; }
        return this.t > 22.5;
      } },
      T.call((a) => { if (sc.caught === true) { a.play('Idle', 0.2); a.lookTarget = () => R.holder.position; } }),
      { start(a) { this.l = sc.caught === true ? a.play('Punch', 0.15) * 0.8 : 0; if (sc.caught === true) onSay(a.key, fresh(['TAG!', 'Gotcha!', 'Tag, you are it!']), 2, 'play'); }, update(a, dt) { this.l -= dt; return this.l <= 0; } },
      T.call((a) => {
        if (sc.caught === true) {
          a.face('laugh', 3); a.remember(`Tagged ${R.s.name} in the garden`, null, 'social'); R.remember(`${a.s.name} caught me at tag`, null, 'social');
          const r = rel(a, R); r.wins[a.key] = (r.wins[a.key] || 0) + 1; bond(a, R); a.feel(0.2, -0.15, -0.1); R.feel(0.08, -0.15, -0.05);
        } else { a.face('tired', 3); onSay(a.key, 'So… out of… breath…', 2.4, 'play'); a.feel(0.05, -0.2, 0); }
      }), T.anim('Yes'), T.wait(1.5), T.call(() => sc.end()), leave(sc));
    return true;
  }

  /** Everyone free meets in the meeting room. A results review uses the run's real numbers. */
  function meeting(people, review) {
    lastMeeting = clock;
    const f = facts();
    const host = review ? agents.rank : people.find((p) => p.key === 'plan') || people[0];
    const seats = meetChairs.filter((s) => !s.busy);
    const attendees = people.filter((p) => p !== host).slice(0, seats.length);
    const runner = !review && attendees.length >= 3 && Math.random() < 0.35 ? attendees.pop() : null;   // slips out instead
    const m = { arrived: 0, n: attendees.length + 1, done: false, cancelled: false };
    const lines = review
      ? [`Results review — ${f.fits} roles fit you`, f.scored ? `We analysed ${f.scored} jobs, ${f.rejected} were not a fit` : 'Every job was checked against your profile',
        f.top ? `Best match so far: ${f.top}` : 'Each score comes with the reasons', 'Great work, team. Party in the garden!']
      : [fresh(['Quick sync, team', 'Stand-up time', 'Two-minute huddle']), 'Reminder: company boards first — fewer applicants there',
        'Fresh postings first; old ones get a warning', 'And never invent anything on a resume. Thanks!'];
    if (runner) {
      lines.splice(1, 0, `Wait — has anyone seen the ${runner.s.name}?`);
      const hide = pick([...SPOTS.garden, ...SPOTS.gameNook].filter((x) => !x.busy));
      if (hide) {
        claim(runner, hide);
        runner.pushIdle(...leaveSeat(runner), T.doing('escaping a meeting'), T.face('sneaky', 12),
          T.say(fresh(['Not another meeting…', 'I was never here.', 'Quietly… quietly…']), 2.2, 'chat'), T.sneak(() => hide.pos), T.face('laugh', 3), T.wait(rand(6, 10)),
          T.call((a) => { a.doing = ''; a.remember(`Escaped a meeting run by the ${host.s.name}`, null, 'social'); }));
        runner.nextIdle = clock + 50;
        if (Math.random() < 0.45) pendingEnds.push({ A: host, B: runner, end: { type: 'chase', chaser: 0 }, at: clock + 32 });
      }
    }
    for (const p of [host, ...attendees]) { if (p.scene) p.scene.cancel(); p.meeting = m; if (p.convo) { p.convo.cancelled = true; p.convo = null; } p.queue = p.queue.filter((t) => !t.idle); if (p.task && p.task.idle) p.task = null; }
    host.pushIdle(...leaveSeat(host), T.doing('running a meeting'), T.go(() => PRESENTER.pos), T.faceAngle(PRESENTER.face), T.call(() => { m.arrived++; }),
      T.until(() => m.arrived >= m.n || m.cancelled, 40), T.focus(() => V(21, -3)));
    lines.forEach((text, i) => host.pushIdle(T.call((a) => { if (!m.cancelled) { onSay(a.key, text, 3.4, 'chat'); a.face(i === lines.length - 1 ? 'happy' : 'focused', 3); } }), T.anim(i === 0 ? 'Wave' : i === lines.length - 1 ? 'ThumbsUp' : 'Yes'), T.wait(2.2)));
    host.pushIdle(T.call(() => { m.done = true; if (review) partyAt = clock + 6; }), T.wait(1), T.call((a) => { a.meeting = null; a.doing = ''; }));
    attendees.forEach((p, i) => {
      const seat = seats[i]; claim(p, seat);
      p.pushIdle(...leaveSeat(p), T.doing('in a meeting'), ...T.goSit('chair', seat), T.call((a) => { m.arrived++; a.lookTarget = () => host.holder.position; }),
        T.until(() => m.done || m.cancelled, 70),
        ...(i === 0 ? [T.call((a) => onSay(a.key, review ? 'Nice — let us go apply early!' : fresh(['Got it.', 'Noted.', 'Sure thing.', 'Can we go now?']), 2.6, 'chat'))] : []),
        ...(i === 1 && Math.random() < 0.5 ? [T.call((a) => { a.face('sleepy', 2); onSay(a.key, '…was I asleep?', 2, 'chat'); })] : []),
        T.wait(rand(0.5, 2.5)), T.call((a) => { a.meeting = null; a.doing = ''; a.lookTarget = null; }));
    });
  }
  /** After a finished search and its review: everyone dances in the garden under the lights. */
  function party() {
    const people = list.filter((a) => free(a));
    if (people.length < 3) return;
    throwConfetti(10, 16.5);
    people.forEach((p, i) => {
      if (p.scene) p.scene.cancel();
      const ang = (i / people.length) * Math.PI * 2, spot = V(12.5 + Math.cos(ang) * 3.2, 16.4 + Math.sin(ang) * 2.4);
      p.pushIdle(...leaveSeat(p), T.doing('partying'), T.go(() => spot), T.faceAngle(Math.atan2(12.5 - spot.x, 16.4 - spot.z)), T.face(pick(['laugh', 'happy', 'love']), 9),
        ...(i === 0 ? [T.say(fresh(['PARTY!', 'Music, please!', 'Everybody dance!']), 2.4, 'play')] : i === 1 ? [T.say(fresh(['Naatu naatu!', 'Best team in Hyderabad!', 'DJ, drop the beat!']), 2.4, 'play')] : []),
        T.call((a) => { a.danceUntil = clock + 9; }), T.loop('Dance', 9), T.call((a) => { a.feel(0.25, -0.1, -0.2); a.doing = ''; }));
      bond(p, people[(i + 1) % people.length]);
    });
    focus = V(12.5, 16.4); focusUntil = clock + 12;
  }

  let directorT = 0;
  function director(dt) {
    directorT -= dt; if (directorT > 0) return; directorT = 0.5;
    runEnds();
    const freeNow = list.filter(free);
    if (reviewAt && clock > reviewAt && !runActive && freeNow.length === list.length) { reviewAt = 0; meeting(list, true); return; }
    if (partyAt && clock > partyAt && !runActive) { partyAt = 0; party(); return; }
    if (!runActive && freeNow.length >= 6 && clock - lastMeeting > 300 && Math.random() < 0.03) { meeting(freeNow, false); return; }
    for (const a of freeNow.sort(() => Math.random() - 0.5)) {
      if (clock < a.nextIdle || a.busy) continue;
      const others = freeNow.filter((o) => o !== a && !o.busy && !o.convo && !o.scene && clock >= o.nextIdle - 4);
      const r = Math.random();
      a.nextIdle = clock + rand(16, 32);
      if (a.mood.energy < 0.3 && r < 0.7) { nap(a); continue; }
      if (!runActive && jealousOf(a) && r < 0.35 && jealousWatch(a)) continue;
      // someone holding a grudge does not pick its enemy for a friendly chat (but a fight may still find them)
      const B = others.length ? pick(others.filter((o) => grudgeOf(a) !== o.key) .concat(r < 0.15 ? others : [])) || null : null;
      // while a search runs, done agents only take quiet breaks
      if (runActive) {
        if (B && r < 0.55) { const pair = takeSpotPair(['pantryTable', 'cooler', 'lounge']); if (pair) { converse(a, B, pair); B.nextIdle = a.nextIdle; continue; } }
        if (r < 0.8) coffeeBreak(a); else wander(a);
        continue;
      }
      if (B && r < 0.34) {
        const pair = takeSpotPair(['pantryTable', 'cooler', 'lounge', 'floorA', 'floorB', 'garden', 'gameNook', 'bench']);
        if (pair) { converse(a, B, pair); B.nextIdle = a.nextIdle; continue; }
      }
      if (B && r < 0.46 && duel('pingpong', a, B)) { B.nextIdle = a.nextIdle; continue; }
      if (B && r < 0.53 && duel('foosball', a, B)) { B.nextIdle = a.nextIdle; continue; }
      if (B && r < 0.6 && tag(a, B)) { B.nextIdle = a.nextIdle; continue; }
      if (B && r < 0.65 && playFight(a, B)) { B.nextIdle = a.nextIdle; continue; }
      if (r < 0.69 && sneakSnack(a)) continue;
      if (r < 0.72) { arcade(a); continue; }
      if (r < 0.73) { swingRide(a); continue; }
      if (r < 0.77) { wish(a); continue; }
      if (r < 0.81) { soloDance(a); continue; }
      if (r < 0.92) { coffeeBreak(a); continue; }
      wander(a);
    }
  }

  // ------------------------------------------------------------------ live boards (real numbers only)
  let boardSig = '';
  function drawBoards() {
    const c = world.counts || {}, st = world.status || 'idle';
    const sig = JSON.stringify([c.search_results, c.candidates, c.recommended, c.scored, c.rejected, st, world.total, document.documentElement.dataset.theme]);
    if (sig === boardSig) return; boardSig = sig;
    const rows = [['Search results', c.search_results], ['Postings read', c.candidates], ['Analysed', world.total ? `${c.scored || 0} / ${world.total}` : c.scored],
      ['Fit you', c.recommended], ['Not a fit', c.rejected]];
    const label = st === 'running' || st === 'queued' ? 'LIVE · searching' : st === 'completed' ? 'Last search' : st === 'idle' || !st ? 'No search yet' : st;
    { const g = boardTex.image.getContext('2d'), W = 1024, H = 512;
      g.fillStyle = '#14161b'; g.fillRect(0, 0, W, H);
      g.fillStyle = st === 'running' || st === 'queued' ? '#ff7a45' : '#7fd1a3'; g.font = '700 40px system-ui, sans-serif'; g.fillText(label, 48, 74);
      g.font = '500 34px system-ui, sans-serif';
      rows.forEach(([k, v], i) => { g.fillStyle = '#9aa3b2'; g.fillText(k, 48, 150 + i * 70); g.fillStyle = '#ffffff'; g.font = '700 40px system-ui, sans-serif'; g.fillText(v == null || v === '' ? '—' : String(v), 640, 150 + i * 70); g.font = '500 34px system-ui, sans-serif'; });
      boardTex.needsUpdate = true; }
    { const g = tickerTex.image.getContext('2d'), W = 1024, H = 320;
      g.fillStyle = '#14161b'; g.fillRect(0, 0, W, H);
      g.fillStyle = st === 'running' || st === 'queued' ? '#ff7a45' : '#7fd1a3'; g.font = '700 46px system-ui, sans-serif'; g.fillText(label, 40, 82);
      g.fillStyle = '#ffffff'; g.font = '600 60px system-ui, sans-serif';
      g.fillText(`${c.search_results ?? '—'} found · ${c.recommended ?? '—'} fit you`, 40, 196);
      g.fillStyle = '#9aa3b2'; g.font = '500 38px system-ui, sans-serif';
      g.fillText(world.total ? `${c.scored || 0} of ${world.total} analysed` : 'Waiting for the next search', 40, 270);
      tickerTex.needsUpdate = true; }
  }

  // ------------------------------------------------------------------ theme
  let isDarkNow = dark;
  function setTheme(isDark) {
    isDarkNow = isDark;
    for (const [m, fn] of [[floorMat, () => plankTexture(isDark)], [grass, () => grassTexture(isDark)], [gameFloor, () => rubberTexture(isDark)],
      [pantryFloor, () => tileTexture(isDark ? '#3b3a3f' : '#f3efe6', isDark ? '#2f2e33' : '#e2d9c8')],
      [serverFloor, () => tileTexture(isDark ? '#1d2027' : '#c9ced8', isDark ? '#23272f' : '#bcc2cd', 6)]]) {
      if (m.map) m.map.dispose(); m.map = fn(); m.needsUpdate = true;
    }
    const bg = isDark ? 0x15161b : 0xefe9e1;
    scene.background = new THREE.Color(bg);
    scene.fog = new THREE.Fog(bg, 150, 260);
    ground.material.color.set(isDark ? 0x1b1c22 : 0xe8e1d7);
    slabMat.color.set(isDark ? 0x2a2a31 : 0xd9cfc2);
    wallMat.color.set(isDark ? 0x2c2c33 : 0xf4ede4);
    partMat.color.set(isDark ? 0x35353d : 0xe9e0d4);
    trimMat.color.set(isDark ? 0x3a3a43 : 0xd8cabb);
    carpet.color.set(isDark ? 0x2f3850 : 0x6d7fa3);
    hemi.color.set(isDark ? 0xaab4ff : 0xfff6ec); hemi.groundColor.set(isDark ? 0x15151b : 0xc9b8a6);
    hemi.intensity = isDark ? 0.35 : 0.55; sun.intensity = isDark ? 0.9 : 2.4; sun.color.set(isDark ? 0xb8c4ff : 0xfff0dc);
    scene.environmentIntensity = isDark ? 0.28 : 0.5;
    fill.intensity = isDark ? 44 : 16;
    pools.forEach((m, i) => { m.opacity = isDark ? (i === pools.length - 1 ? 0.16 : 0.34) : 0.05; });
    bulbM.emissiveIntensity = isDark ? 3 : 0.35;
    renderer.toneMappingExposure = isDark ? 1.18 : 1.0;
    boardSig = '';
    renderer.shadowMap.needsUpdate = true;
  }
  setTheme(dark);

  // ------------------------------------------------------------------ camera & pointer
  const VIEWS = {
    all: { look: V(1, 6.2, 0.4), r: null },
    work: { look: V(0, 0.2, 0.4), r: 32 },
    meeting: { look: V(21, -2, 0.2), r: 21 },
    pantry: { look: V(-20, 6, 0.2), r: 18 },
    server: { look: V(-20, -6, 0.2), r: 18 },
    game: { look: V(-13, 16.2, 0.2), r: 22 },
    garden: { look: V(12.5, 16.2, 0.2), r: 24 },
  };
  const cam = { theta: 0, phi: 0.82, phiNow: 0.82, r: 60, base: 60, zoomed: false, userUntil: 0, follow: true, rNow: null, view: 'all' };
  const look = VIEWS.all.look.clone();
  let dragging = null;
  const el = renderer.domElement;
  el.style.touchAction = 'none';
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function agentAt(e) {
    const r = el.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables.filter((m) => m.visible && agents[m.userData.agentKey].holder.visible), false)[0];
    return hit ? hit.object.userData.agentKey : null;
  }
  const onDown = (e) => { dragging = { x: e.clientX, y: e.clientY, theta: cam.theta, phi: cam.phi, moved: false }; el.setPointerCapture(e.pointerId); };
  let hoverT = 0;
  const onMove = (e) => {
    if (dragging) {
      if (Math.hypot(e.clientX - dragging.x, e.clientY - dragging.y) > 4) { dragging.moved = true; el.classList.add('grabbing'); }
      if (!dragging.moved) return;
      cam.theta = Math.max(-1.1, Math.min(1.1, dragging.theta - (e.clientX - dragging.x) * 0.005));
      cam.phi = Math.min(1.3, Math.max(0.38, dragging.phi - (e.clientY - dragging.y) * 0.005));
      cam.userUntil = performance.now() + 9000;
      return;
    }
    const now = performance.now(); if (now - hoverT < 60) return; hoverT = now;
    hovered = agentAt(e);
    el.style.cursor = hovered ? 'pointer' : '';
  };
  const onUp = (e) => {
    const click = dragging && !dragging.moved;
    dragging = null; el.classList.remove('grabbing');
    if (click) select(agentAt(e));
  };
  const onLeave = () => { hovered = null; el.style.cursor = ''; };
  const onWheel = (e) => { e.preventDefault(); cam.r = Math.min(100, Math.max(9, cam.r + Math.sign(e.deltaY) * 2.8)); cam.zoomed = true; cam.userUntil = performance.now() + 9000; };
  el.addEventListener('pointerdown', onDown); el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerup', onUp); el.addEventListener('pointercancel', onUp); el.addEventListener('pointerleave', onLeave);
  el.addEventListener('wheel', onWheel, { passive: false });

  /** Click a robot: the camera goes to it and it says hello (or what it is doing). */
  function select(key) {
    selected = key && agents[key] ? key : null;
    onSelect(selected);
    if (!selected) return;
    const a = agents[selected];
    if (!a.hasWork && !a.convo && !a.meeting && !a.scene && a.doing !== 'napping') {
      a.pushIdle(...(a.seated ? [] : [T.faceAngle(() => cam.theta), T.anim('Wave')]), T.say(a.s.intro, 4, 'chat'));
      a.face('happy', 2);
    } else if (a.doing === 'napping') onSay(a.key, 'z z z… (shh, it is napping)', 2.4, 'think');
  }
  function view(name) {
    if (!VIEWS[name]) return;
    cam.view = name; cam.zoomed = false; cam.theta = 0; cam.phi = 0.82;
    cam.userUntil = name === 'all' ? 0 : performance.now() + 25000;
    if (selected) select(null);
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w / h < 1.3 ? 42 : 32;
    camera.updateProjectionMatrix();
    const aspect = w / h;
    cam.base = Math.max(44, Math.min(100, 28 + 64 / aspect));          // the whole floor (all rooms) fits
    if (!cam.zoomed) cam.r = cam.base;
  }
  const ro = new ResizeObserver(resize); ro.observe(container); resize();

  // ------------------------------------------------------------------ main loop
  let raf = 0, last = performance.now(), visible = true, disposed = false;
  const tagPos = new THREE.Vector3();
  let frameCb = null;
  let boardT = 0, saveT = 0;
  const perf = { n: 0, sum: 0, checked: false };
  const confObj = new THREE.Object3D();
  function frame(now) {
    raf = 0; if (disposed) return;
    // 30 frames a second is smooth for robots walking about and halves GPU/CPU work; 60 only while the person moves
    // the camera or something flies through the air
    const lively = dragging || performance.now() < cam.userUntil || flying.length > 0 || confetti.visible;
    if (!lively && now - last < 1000 / 30 - 3) { schedule(); return; }
    const tFrame = performance.now();
    const rawDt = (now - last) / 1000;
    let dt = Math.min(0.12, rawDt); last = now;
    clock += dt;
    // quality: if this machine cannot keep ~24 fps, drop the pixel ratio to 1 (once)
    if (!perf.checked && clock > 2.5 && rawDt < 0.5) { perf.n++; perf.sum += rawDt; if (perf.n >= 60) { perf.checked = true; if (perf.sum / perf.n > 1 / 24 && pixelRatio > 1) { pixelRatio = 1; renderer.setPixelRatio(1); resize(); } } }
    const load = queueLoad();
    speed = load > 40 ? 2.2 : load > 20 ? 1.6 : 1;
    if (reducedMotion) dt *= 0.0001;
    director(dt);
    for (const sc of scenes) if (sc.tick) sc.tick(dt);
    for (const a of list) {
      for (const [n, act] of Object.entries(a.actions)) {
        if (!act.isRunning()) continue;
        act.setEffectiveTimeScale(STRIDE[n] && a.moveRate ? (a.moveRate * speed) / STRIDE[n] : speed);
      }
      // mood drifts: work tires, breaks restore; joy returns to its usual level
      const m = a.mood;
      if (a.hasWork) { m.energy = clamp(m.energy - dt * 0.004, 0, 1); m.stress = clamp(m.stress + dt * 0.002, 0, 1); }
      else { m.stress = clamp(m.stress - dt * 0.004, 0, 1); m.energy = clamp(m.energy + dt * (a.seated ? 0.004 : 0.0008), 0, 1); }
      m.joy += (0.6 - m.joy) * dt * 0.004;
      a.update(dt);
      if (a.danceUntil && clock < a.danceUntil && Math.random() < dt * 2.2) emitNote(worldPos(a.holder).setY(ROBOT_HEIGHT + 0.3), a.s.hue);
    }
    // nobody stands inside anybody: standing robots closer than MIN_GAP ease apart (seated ones stay put and push)
    for (let i = 0; i < list.length; i++) {
      const A = list[i];
      if (!A.holder.visible || A.riding) continue;
      for (let j = i + 1; j < list.length; j++) {
        const B = list[j];
        if (!B.holder.visible || B.riding || (A.seated && B.seated)) continue;
        const pa = A.holder.position, pb = B.holder.position;
        let dx = pb.x - pa.x, dz = pb.z - pa.z;
        const d = Math.hypot(dx, dz);
        if (d >= MIN_GAP) continue;
        if (d < 1e-3) { dx = 1; dz = 0; } else { dx /= d; dz /= d; }
        const push = (MIN_GAP - d) * Math.min(1, dt * 8);
        const ka = A.seated ? 0 : B.seated ? 1 : 0.5, kb = 1 - ka;
        pa.x -= dx * push * ka; pa.z -= dz * push * ka;
        pb.x += dx * push * kb; pb.z += dz * push * kb;
      }
    }
    // the swing (and whoever rides it)
    swingT += dt;
    const sAng = Math.sin(swingT * 1.9) * swingAmp;
    swing.rotation.x = sAng;
    for (const a of list) if (a.riding) { const sp = worldPos(seat); a.holder.position.set(sp.x, sp.y + 0.035 - SIT_DROP, sp.z + SIT_FWD); a.holder.rotation.x = sAng; }
    for (let i = flying.length - 1; i >= 0; i--) {
      const f = flying[i]; f.t += (dt * speed) / f.d;
      const u = Math.min(1, f.t);
      f.p.position.lerpVectors(f.from, f.to, u);
      if (f.plane) { f.p.position.y += Math.sin(Math.PI * u) * 2.2; const nx = f.to.clone().sub(f.from); f.p.rotation.set(0, Math.atan2(nx.x, nx.z), Math.sin(u * 8) * 0.3); f.p.scale.setScalar(1 - Math.max(0, u - 0.8) * 5); }
      else { f.p.position.y += Math.sin(Math.PI * u) * 1.6; f.p.rotation.set(u * 3, u * 5, u * 2); }
      if (u >= 1) { scene.remove(f.p); flying.splice(i, 1); if (f.onLand) f.onLand(); }
    }
    for (let i = tweens.length - 1; i >= 0; i--) { const tw = tweens[i]; tw.t += dt; const k = Math.min(1, tw.t / tw.d); tw.fn(1 - Math.pow(1 - k, 3)); if (k >= 1) tweens.splice(i, 1); }
    for (let i = notes.length - 1; i >= 0; i--) { const n = notes[i]; n.t += dt; n.s.position.y += dt * 0.9; n.s.position.x = n.x0 + Math.sin(n.t * 3 + n.ph) * 0.3; n.s.material.opacity = 1 - n.t / 2; if (n.t > 2) { scene.remove(n.s); n.s.material.dispose(); owned.delete(n.s.material); notes.splice(i, 1); } }
    if (confetti.visible) {
      conf.forEach((c, i) => { c.p.addScaledVector(c.v, dt); c.v.x += Math.sin(clock * 2 + i) * dt * 0.3; c.r.x += dt * c.s; c.r.y += dt * c.s * 0.7; if (c.p.y < 0.05) c.p.y = 0.05; confObj.position.copy(c.p); confObj.rotation.copy(c.r); confObj.updateMatrix(); confetti.setMatrixAt(i, confObj.matrix); });
      confetti.instanceMatrix.needsUpdate = true;
      if (clock > partyUntil) confetti.visible = false;
    }
    // props react to their agent's work
    const Pt = stations.discover.portal;
    portalFlash = Math.max(0, portalFlash - dt * 1.6);
    const scoutWorking = stateMap.discover === 'running';
    Pt.veil.material.opacity = 0.22 + (scoutWorking ? 0.15 + Math.sin(clock * 4) * 0.08 : 0) + portalFlash * 0.6;
    Pt.ringM.emissiveIntensity = 0.8 + (scoutWorking ? Math.sin(clock * 4) * 0.4 : 0) + portalFlash * 2;
    stations.discover.globe.rotation.y += dt * (scoutWorking ? 1.4 : 0.2);
    stampHit = Math.max(0, stampHit - dt * 2.5);
    stations.validate.stamp.position.y = 1.06 + Math.sin(stampHit * Math.PI) * 0.35;
    for (const key of ['understand', 'match', 'connect']) { const sc = stations[key].screen; if (sc) sc.material.emissiveIntensity = stateMap[key] === 'running' ? 0.8 + Math.sin(clock * 7) * 0.2 : 0.35; }
    stations.plan.lines.forEach((l, i) => { l.scale.x = stateMap.plan === 'running' ? 0.55 + 0.45 * Math.abs(Math.sin(clock * 1.4 + i)) : stateMap.plan === 'done' ? 1 : 0.4; });
    const ratio = world.scoredRatio || 0;
    stations.match.bars.forEach((b, i) => { const goal = stateMap.match === 'done' ? 0.55 + i * 0.25 : 0.15 + ratio * (0.6 + i * 0.3); b.scale.y += (goal - b.scale.y) * Math.min(1, dt * 3); b.position.y = 1.07 + b.scale.y / 2; });
    stations.rank.trophy.rotation.y += dt * (celebrated ? 2.4 : 0.3);
    stations.connect.people.forEach((p, i) => { p.scale.setScalar(stateMap.connect === 'running' ? 1 + Math.max(0, Math.sin(clock * 3 + i * 1.3)) * 0.12 : 1); });
    for (const s of STATIONS) stations[s.key].pad.material.opacity = stateMap[s.key] === 'running' ? 0.22 + Math.sin(clock * 3) * 0.08 : stateMap[s.key] === 'done' ? 0.16 : 0.07;
    serverBusy = Math.max(0, serverBusy - dt);
    const blink = scoutWorking || serverBusy > 0 ? 9 : 2.2;
    ledMats.forEach((m, i) => { m.emissiveIntensity = 0.5 + 0.9 * (Math.sin(clock * blink * (1 + i * 0.37) + i * 2) > 0.2 ? 1 : 0.2); });
    brewing = Math.max(0, brewing - dt);
    for (const s of steam) {
      s.t = (s.t + dt * 0.6) % 1;
      s.p.visible = brewing > 0;
      s.p.position.set(-24.15 + Math.sin(s.t * 9) * 0.05, 1.95 + s.t * 1.1, 4.4);
      s.p.scale.setScalar(0.6 + s.t * 1.6); s.p.material.opacity = (1 - s.t) * 0.45;
    }
    for (const j of jet) { j.t = (j.t + dt * 0.7) % 1; const r = j.t * 0.9; j.d.position.set(FOUNT.x + Math.cos(j.a) * r, 1.45 + Math.sin(j.t * Math.PI) * 0.7 - j.t * 0.9, FOUNT.z + Math.sin(j.a) * r); }
    for (const rp of ripples) { if (rp.t < 1) { rp.t += dt * 0.8; rp.r.scale.setScalar(1 + rp.t * 4); rp.r.material.opacity = (1 - rp.t) * 0.7; } else rp.r.material.opacity = 0; }
    water.material.emissiveIntensity = 0.22 + Math.sin(clock * 1.5) * 0.05;
    for (const a of arcades) drawArcade(a, dt);
    boardT -= dt; if (boardT <= 0) { boardT = 1; drawBoards(); drawClock(); }
    saveT -= dt; if (saveT <= 0) { saveT = 8; if (saveDirty) { saveDirty = false; writeSaved(saved); } }

    // camera: a chosen room, a selected robot, or wherever the action is
    const userHolds = performance.now() < cam.userUntil;
    const sel = selected && agents[selected];
    const following = cam.follow && focus && clock < focusUntil && !userHolds && !sel;
    let goal, r;
    if (sel) { goal = sel.holder.position.clone().setY(1.2); r = 10.5; }
    else if (following) { goal = V(clamp(focus.x, -19, 20), clamp(focus.z, -4, 17), 0.6); r = cam.zoomed ? cam.r : Math.min(cam.base * 0.6, 36); }
    else { const v = VIEWS[cam.view]; goal = v.look; r = cam.zoomed ? cam.r : v.r || cam.base; }
    look.lerp(goal, Math.min(1, dt * 1.8));
    cam.rNow = cam.rNow == null ? r : cam.rNow + (r - cam.rNow) * Math.min(1, dt * 1.8);
    cam.phiNow += ((sel && !userHolds ? 1.12 : cam.phi) - cam.phiNow) * Math.min(1, dt * 2);
    const ph = cam.phiNow;
    camera.position.set(look.x + Math.sin(cam.theta) * Math.sin(ph) * cam.rNow, look.y + Math.cos(ph) * cam.rNow, look.z + Math.cos(cam.theta) * Math.sin(ph) * cam.rNow);
    camera.lookAt(look);
    renderer.render(scene, camera);
    perf.cpu = (perf.cpu || 0) * 0.95 + (performance.now() - tFrame) * 0.05;
    if (frameCb) {
      const w = container.clientWidth, h = container.clientHeight, out = {};
      for (const [key, a] of Object.entries(agents)) {
        a.holder.getWorldPosition(tagPos); tagPos.y += (a.seated ? ROBOT_HEIGHT * 0.8 : ROBOT_HEIGHT) + 0.3; tagPos.project(camera);
        const ex = clock < a.expr.until ? a.expr.name : a.baseExpr();
        out[key] = { x: (tagPos.x + 1) / 2 * w, y: (1 - tagPos.y) / 2 * h, visible: a.holder.visible && tagPos.z < 1 && tagPos.z > -1, depth: tagPos.z,
          where: roomOf(a.holder.position), seated: !!a.seated, chatting: !!a.convo || !!a.meeting, doing: a.doing, expr: ex };
      }
      frameCb(out);
    }
    schedule();
  }
  function schedule() { if (!raf && visible && !disposed && !document.hidden) raf = requestAnimationFrame(frame); }
  const io = new IntersectionObserver((ents) => { visible = ents.some((e) => e.isIntersecting); last = performance.now(); schedule(); });
  io.observe(container);
  const onVis = () => { last = performance.now(); schedule(); };
  document.addEventListener('visibilitychange', onVis);
  // compile every shader before the first frame (in parallel where the GPU driver allows), so opening the office
  // shows the loading note a moment longer instead of freezing the page on the first frames
  if (renderer.extensions.has('KHR_parallel_shader_compile')) { try { await renderer.compileAsync(scene, camera); } catch { /* compiles on first use */ } }
  schedule();
  // a tiny handle for measuring render cost from the browser console (no effect unless used)
  window.__jhxOffice = { renderer, baked, select: (k) => select(k), view: (v) => view(v), info: () => renderer.info.render, cpu: () => perf.cpu,
    /** try a scene: __jhxOffice.scene('argument', 'discover', 'dedupe') — argument | satire | jealous | scheme | banter | chase | fight | sneak */
    scene(kind, a, b) {
      const A = agents[a], B = agents[b]; if (!A || !B) return false;
      for (const X of [A, B]) { if (X.scene) X.scene.cancel(); X.queue = X.queue.filter((t) => !t.idle); if (X.task && X.task.idle) X.task = null; X.nextIdle = clock + 60; }
      if (kind === 'chase') return chase(A, B);
      if (kind === 'fight') return playFight(A, B);
      if (kind === 'sneak') return sneakSnack(A, B);
      const pair = takeSpotPair(['floorA', 'floorB', 'lounge', 'garden']);
      return !!(pair && converse(A, B, pair, '', kind));
    } };

  return {
    /** stage states + live numbers from the run */
    update(states, extra = {}) {
      Object.assign(world, extra);
      stateMap = states;
      runActive = ['queued', 'running'].includes(world.status);
      for (const [key, st] of Object.entries(states)) if (agents[key]) agents[key].state = st;
    },
    /** activity items of the run, oldest first; only new ones become scenes */
    feed(items, id, finished, recent) {
      if (id !== runId) reset(id);
      if (lastId === null) {
        const replay = recent ? Math.min(recent === 'all' ? 60 : 20, items.length) : 0;
        if (!replay) { lastId = items.length ? items[items.length - 1].id : 0; if (finished) celebrated = true; return; }
        const first = items.length - replay;
        lastId = first > 0 ? items[first - 1].id : -1;
      }
      for (const it of items) if (it.id > lastId) { lastId = it.id; onEvent(it); }
    },
    setTheme,
    setFollow(on) { cam.follow = on; },
    setAI(on) { aiOn = !!on; },
    onFrame(cb) { frameCb = cb; },
    resetView() { Object.assign(cam, { theta: 0, phi: 0.82, r: cam.base, zoomed: false, userUntil: 0, view: 'all' }); select(null); },
    view,
    select,
    /** What the card shows for one agent: mood, what it is doing, memories, friends. */
    info(key) {
      const a = agents[key]; if (!a) return null;
      const f = friendsOf(a);
      return { mood: { ...a.mood }, doing: a.doing, expr: clock < a.expr.until ? a.expr.name : a.baseExpr(),
        memories: a.mem.slice(0, 5).map((m) => ({ text: m.text, from: m.from ? nameOf(m.from) : null, kind: m.kind })), best: f.best, rival: f.rival,
        grudge: grudgeOf(a) ? { key: grudgeOf(a), name: nameOf(grudgeOf(a)) } : null };
    },
    /** The person pokes an agent. */
    poke(key) {
      const a = agents[key]; if (!a) return;
      if (a.doing === 'napping') { a.doing = ''; a.face('scared', 2); a.queue = a.queue.filter((t) => !t.idle); a.task = null; a.pushIdle(T.stand(), T.anim('Jump'), T.say('WHA— I was not sleeping!', 2.4, 'play'), T.face('angry', 2)); return; }
      a.face(pick(['surprised', 'laugh', 'wink']), 2.2); a.feel(0.08, 0, 0);
      onSay(a.key, fresh(['Hey! That tickles!', 'Who did that?!', 'I am working… sort of', 'Boop!', 'Careful, I bite. (I do not.)', 'Hi there, human!']), 2.4, 'play');
      if (!a.seated && !a.hasWork && !a.scene) a.gesture(pick(['Jump', 'Wave', 'Yes']));
    },
    /** Send a free agent on a break (chai, a nap if tired). */
    rest(key) {
      const a = agents[key]; if (!a) return false;
      if (!free(a)) { onSay(a.key, a.hasWork ? 'After this job — promise!' : 'Already relaxing!', 2.4, 'chat'); return false; }
      a.queue = a.queue.filter((t) => !t.idle); a.task = null; a.nextIdle = clock + 30;
      if (a.mood.energy < 0.35) nap(a); else coffeeBreak(a);
      return true;
    },
    /** Show a line from outside (an answer to the person's question) on the agent, with a face. */
    speak(key, text, emotion = 'happy', secs = 7, kind = 'ask') {
      const a = agents[key]; if (!a) return;
      onSay(a.key, text, secs, kind); a.face(emotion, secs);
      if (!a.seated && !a.hasWork && !a.scene && !a.convo) a.pushIdle(T.faceAngle(() => cam.theta), T.anim('Yes'));
    },
    thinking(key, on) { const a = agents[key]; if (!a) return; if (on) { a.face('focused', 15); onSay(a.key, '…', 15, 'think'); } else a.expr.until = 0; },
    dispose() {
      disposed = true; cancelAnimationFrame(raf);
      if (saveDirty) writeSaved(saved);
      ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', onVis);
      el.removeEventListener('pointerdown', onDown); el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerup', onUp); el.removeEventListener('pointercancel', onUp); el.removeEventListener('pointerleave', onLeave);
      el.removeEventListener('wheel', onWheel);
      for (const a of list) a.mixer.stopAllAction();
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) owned.add(o.material); });
      for (const m of [floorMat, pantryFloor, serverFloor, grass, gameFloor]) if (m.map) m.map.dispose();
      boardTex.dispose(); tickerTex.dispose(); clockTex.dispose(); noteTex.dispose(); faceTextures.forEach((t) => t.dispose());
      for (const a of arcades) a.tex.dispose();
      owned.forEach((m) => { if (m.map) m.map.dispose(); if (m.dispose) m.dispose(); });
      envTex.dispose();
      renderer.dispose(); el.remove();
    },
  };
}

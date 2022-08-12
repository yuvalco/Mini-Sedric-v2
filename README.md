# Mini sedric
## AWS Serverless Lambda appliction

Serverless application that detects similarities and matches in an audio file.
* Uses Spacy
* AWS Lambda
* AWS Transcribe
* S3 bucket storage
* Mypy/ Python type annotations

## How to run

After running sam local start-api go to this address
```sh
http://127.0.0.1:3000/hello?
```

## Parameters:

| Parameters | data |
| ------ | ------ |
| interaction_url | s3:// url  |
| trackers | List of search terms like - ["dog", "cat"] |

## Example:
```sh
http://127.0.0.1:3000/hello?interaction_url=<url goes here>&trackers=["hello sir, how are you?"]
```

## Results:

#### Transcript:

		Bay Area Donald trump supporters will get a chance to see him again. Soon,the former president will be
		speaking to kick off his Save America Tour Mr trump is set to appear at a rally at the Sarasota County
		Fairgrounds on july 3rd, doors open at two and the speech is set for eight, followed by fireworks. "

#### Similarities:
| Searched | Found |
| ------ | ------ |
| is expected to make an appearance at a rally. |is set to appear at a rally  |

#### Input example:
     ["is expected to make an appearance at a rally.", "chance to see him again", "wow"]

#### Output example:
```sh
[
    {
        "sentence_idx": 0,
        "start_word_idx": 8,
        "end_word_idx": 12,
        "tracker_value": "chance to see him again",
        "transcribe_value": "chance to see him again"
    },
    {
        "sentence_idx": 1,
        "start_word_idx": 17,
        "end_word_idx": 23,
        "tracker_value": "is expected to make an appearance at a rally.",
        "transcribe_value": "is set to appear at a rally"
    }
```

#### Transcript:

		overseas tonight to Afghanistan where the U. S. Has departed Bagram airfield with little fanfare and
        withdraw all its troops from there. One step closer to drawing America's longest war to a close. NBC's chief
        global affairs anchor Martha Raddatz is just back from Afghanistan where she flew with the U. S. Commander
        on his last helicopter ride out of Bagram. And what he said he's concerned about when the U. S. Is gone. It
        was clear when we visited Bagram airfield last week that U. S. And coalition forces would all soon depart.
        General scott Miller circling the 14 square mile base. The fighter jets gone and heavy equipment as well and
        on the ground. Only a few dozen troops inside once the order for full withdrawal came, this became one of
        the largest and fastest movement of equipment since World War Two outside the gates. Today, only Afghan
        forces remain a force already facing dire circumstances as the Taliban sweep through the country with some
        in the intelligence community predicting the government here could fall in as little as six months. But
        President biden today tried to brush aside those concerns. I met with the Afghan government here in the
        White House in the oval. I think they have the capacity to be able to sustain the government to follow on
        that thought on Afghanistan. how are you today sir? Uh happy things. But there is no happy talk in Afghanistan. Even with some 650 
        troops remaining to protect the embassy and Kabul Airport.he worries about civil war and worse.
        How alarmed are you? The loss of terrain and the rapidity of that loss of terrain has to be concerning.
        We're starting to create conditions here that won't look good for Afghanistan in the future. That concern
        shared by many. Let's bring in Martha, Raddatz and Martha. General Miller was there in the beginning of the
        war nearly 20 years ago when we went into Afghanistan because of the threat to the homeland after 9 11. How
        much does he still worry about that possibility? Well, he still has serious concerns about that. He said Al
        Qaeda is still in Afghanistan and the threat to the US remains with important reminders. Martha Raddatz for
        us. Thank you. Hi everyone. George Stephanopoulos here. Thanks for checking out the abc news Youtube
        channel. If you'd like to get more videos, show highlights and watch live event coverage, click on the right 
        over here to subscribe to our channel and don't forget to download the abc news after breaking news alerts. 
        Thanks for watching. 
   
#### Similarities:
| Searched | Found |
| ------ | ------ |
| I believe they have the ability to keep the government running. |I think they have the capacity to be able to sustain the government  |     
| he is still concerned about it. |And what he said he's concerned about when the U. S. Is gone. |     
#### Input example:
     ["He is still concerned about it." , "i believe they have the ability to keep the government running"]

#### Output example:
```sh
[
    {
        "sentence_idx": 3,
        "start_word_idx": 0,
        "end_word_idx": 14,
        "tracker_value": "he is still concerned about it.",
        "transcribe_value": "And what he said he's concerned about when the U. S. Is gone."
    },
    {
        "sentence_idx": 12,
        "start_word_idx": 0,
        "end_word_idx": 17,
        "tracker_value": "i believe they have the ability to keep the government running",
        "transcribe_value": "I think they have the capacity to be able to sustain the government to follow on that thought"
    }
]
```

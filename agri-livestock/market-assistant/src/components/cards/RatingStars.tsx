import { Star } from 'lucide-react'

interface RatingStarsProps {
  readonly rating: number
  readonly max?: number
}

export default function RatingStars({ rating, max = 5 }: RatingStarsProps) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: max }, (_, i) => (
        <Star
          key={i}
          size={14}
          className={i < rating ? 'text-neon fill-neon' : 'text-text-muted'}
        />
      ))}
    </div>
  )
}
